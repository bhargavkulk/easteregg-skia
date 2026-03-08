#include "easteregg/easteregg.h"

#include "include/core/SkColor.h"
#include "include/core/SkPaint.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecords.h"
#include "src/core/SkRuntimeEffectPriv.h"
#include "src/effects/colorfilters/SkColorFilterBase.h"
#include "src/shaders/SkShaderBase.h"

#define IS_RECORD(isRecord) records->mutate(i, isRecord)

bool isPaintPlain(SkPaint* paint, bool testForOpaque) {
    if (!paint) {
        return true;
    }

    if (paint->getShader() || paint->getColorFilter() || paint->getImageFilter() ||
        paint->getMaskFilter()) {
        return false;
    }

    return (testForOpaque ? paint->getAlphaf() == 1.0f : true) && paint->isSrcOver();
}

bool isPaintLumaMask(SkPaint* paint, float a, float r, float g, float b) {
    if (!paint) {
        return true;
    }

    if (paint->getPathEffect() || paint->getShader() || !paint->isSrcOver() ||
        paint->getMaskFilter() || paint->getColorFilter() || paint->getImageFilter()) {
        return false;
    }

    SkColor4f color = paint->getColor4f();

    return color.fA == a && color.fR == r && color.fG == g && color.fB == b;
}

bool isPaintLumaLayer(SkPaint* paint) {
    if (!paint) {
        return true;
    }

    if (paint->getPathEffect() || paint->getShader() || !paint->isSrcOver() ||
        paint->getMaskFilter() || paint->getImageFilter()) {
        return false;
    }

    SkColorFilter* filter = paint->getColorFilter();

    if (!filter) {
        return false;
    }

    const SkColorFilterBase* base = as_CFB(filter);
    if (!base || base->type() != SkColorFilterBase::Type::kRuntime) {
        return false;
    }

    if (SkRuntimeEffect* effect = base->asRuntimeEffect()) {
        const uint32_t key = SkRuntimeEffectPriv::StableKey(*effect);
        if (key == static_cast<uint32_t>(SkKnownRuntimeEffects::StableKey::kLuma)) {
            return true;
        }

        // I DON'T LIKE THIS AT ALL
        static constexpr char kLumaSkSL[] = "half4 main(half4 color) {return sk_luma(color.rgb);}";

        const std::string& source = effect->source();
        if (key == 0 && source == kLumaSkSL) {
            return true;
        }
    }

    return false;
}

bool isPaintDstInMask(SkPaint* paint) {
    if (!paint) {
        return false;
    }

    if (paint->getPathEffect() || paint->getShader() || paint->getMaskFilter() ||
        paint->getColorFilter() || paint->getImageFilter()) {
        return false;
    }

    const auto blendMode = paint->asBlendMode();
    if (!blendMode || blendMode.value() != SkBlendMode::kDstIn) {
        return false;
    }

    return paint->getAlphaf() == 1.0f;
}

bool isPaintOpaqueLinearOrRadialGradient(SkPaint* paint) {
    if (!paint) {
        return false;
    }

    if (paint->getPathEffect() || paint->getMaskFilter() || paint->getColorFilter() ||
        paint->getImageFilter() || !paint->isSrcOver()) {
        return false;
    }

    SkShader* shader = paint->getShader();
    if (!shader || !shader->isOpaque()) {
        return false;
    }

    const SkShaderBase::GradientType type = as_SB(shader)->asGradient();
    return type == SkShaderBase::GradientType::kLinear ||
           type == SkShaderBase::GradientType::kRadial;
}

void RemoveOpaqueSaveLayers::operator()(SkRecord* records) { transform(records); }

void RemoveOpaqueSaveLayers::transform(SkRecord* records) const {
    match_count = 0;
    for (int i = 0; i < records->count(); i++) {
        if (records->mutate(i, isSaveLayer)) {
            if (!state_stack.empty()) state_stack.back() = MatchState::Ignore;
            state_stack.push_back(isPaintPlain(isSaveLayer.get()->paint) ? MatchState::Matching
                                                                         : MatchState::Ignore);
            index_stack.push_back(i);
        } else if (records->mutate(i, isSave)) {
            state_stack.push_back(MatchState::Ignore);
            index_stack.push_back(i);
        } else if (records->mutate(i, isDraw)) {
            if (state_stack.empty() || state_stack.back() == MatchState::Ignore) {
                continue;
            }
            if (!isPaintPlain(isDraw.get(), false)) {
                state_stack.back() = MatchState::Ignore;
            }
        } else if (records->mutate(i, isRestore)) {
            if (state_stack.empty()) {
                continue;
            }
            auto state = state_stack.back();
            auto index = index_stack.back();
            state_stack.pop_back();
            index_stack.pop_back();

            if (state == MatchState::Matching) {
                records->replace<SkRecords::Save>(index);
                match_count += 1;
            }
        }
    }
}

void GradientDstInToMasks::transform(SkRecord* records) const {
    int saveCount = 0;
    match_count = 0;
    for (int i = 0; i < records->count(); i++) {
        if (IS_RECORD(isSaveLayer)) {
            SkPaint* paint = isSaveLayer.get()->paint;

            const bool matchesInner = !state_stack.empty() &&
                                      state_stack.back().state == MatchState::OuterFill &&
                                      isPaintDstInMask(paint);
            if (matchesInner) {
                state_stack.back().state = MatchState::Ignore;
                state_stack.push_back({
                        MatchState::MaskLayer,
                        i,
                        saveCount,
                        nullptr,
                });
                continue;
            }

            if (!state_stack.empty() && state_stack.back().state != MatchState::Ignore) {
                state_stack.back().state = MatchState::Ignore;
            }
            state_stack.push_back({
                    MatchState::OuterLayer,
                    i,
                    saveCount,
                    nullptr,
            });
        } else if (IS_RECORD(isSave)) {
            saveCount += 1;
        } else if (IS_RECORD(isRestore)) {
            if (state_stack.empty()) {
                SkASSERTF(saveCount > 0, "unbalanced restore at command %d", i);
                saveCount -= 1;
                continue;
            }
            if (state_stack.back().saveCount < saveCount) {
                saveCount -= 1;
                continue;
            }
            if (state_stack.back().state == MatchState::MaskFill) {
                // SkDebugf("GradientDstInToMasks matched: saveLayer=%d restore=%d\n",
                //          state_stack.back().saveLayerIndex,
                //          i);
                for (int j = state_stack.back().saveLayerIndex; j <= i; j++) {
                    records->replace<SkRecords::NoOp>(j);
                }
                match_count += 1;
            }

            state_stack.pop_back();
        } else if (IS_RECORD(isDraw)) {
            // TODO this large if statement can be made very small
            if (state_stack.empty() || state_stack.back().state == MatchState::Ignore) {
                continue;
            } else if (state_stack.back().state == MatchState::OuterLayer) {
                if (isPaintPlain(isDraw.get(), false)) {
                    state_stack.back().state = MatchState::OuterFill;
                } else {
                    state_stack.back().state = MatchState::Ignore;
                }
            } else if (state_stack.back().state == MatchState::OuterFill) {
                state_stack.back().state = MatchState::Ignore;
            } else if (state_stack.back().state == MatchState::MaskLayer) {
                if (isPaintOpaqueLinearOrRadialGradient(isDraw.get())) {
                    state_stack.back().state = MatchState::MaskFill;
                } else {
                    state_stack.back().state = MatchState::Ignore;
                }
            } else if (state_stack.back().state == MatchState::MaskFill) {
                state_stack.back().state = MatchState::Ignore;
            }
        }
    }
}

void RemoveLoneLuma::transform(SkRecord* records) const {
    int saveCount = 0;
    match_count = 0;
    for (int i = 0; i < records->count(); i++) {
        if (IS_RECORD(isSaveLayer)) {
            if (!state_stack.empty()) {
                state_stack.back().state = MatchState::Ignore;
            }
            SkPaint* paint = isSaveLayer.get()->paint;

            if (paint && isPaintLumaLayer(paint)) {
                state_stack.push_back({
                        MatchState::MatchSaveLayer,
                        i,
                        saveCount,
                        -1,
                        nullptr,
                });
            } else {
                state_stack.push_back({
                        MatchState::Ignore,
                        i,
                        saveCount,
                        -1,
                        nullptr,
                });
            }
        } else if (IS_RECORD(isSave)) {
            saveCount += 1;
        } else if (IS_RECORD(isRestore)) {
            if (state_stack.empty()) {
                SkASSERTF(saveCount > 0, "unbalanced restore at command %d", i);
                saveCount -= 1;
                continue;
            }
            if (state_stack.back().saveCount < saveCount) {
                saveCount -= 1;
                continue;
            }

            if (state_stack.back().state == MatchState::MatchDraw) {
                records->replace<SkRecords::Save>(state_stack.back().index);
                state_stack.back().paint->setColor4f(SkColors::kBlack);
                match_count += 1;
            }

            state_stack.pop_back();
        } else if (IS_RECORD(isDraw)) {
            if (state_stack.empty()) {
                continue;
            } else if (state_stack.back().state == MatchState::MatchDraw) {
                state_stack.back().state = MatchState::Ignore;
            } else if (state_stack.back().state == MatchState::MatchSaveLayer) {
                if (isPaintLumaMask(isDraw.get(), 1.0, 1.0, 1.0, 1.0)) {
                    state_stack.back().state = MatchState::MatchDraw;
                    state_stack.back().ptr = i;
                    state_stack.back().paint = isDraw.get();
                } else {
                    state_stack.back().state = MatchState::Ignore;
                }
            }
        }
    }
}

// TODO need to check if clip after MatchDstin is always id
void DstInToClip::transform(SkRecord* records) const {
    int saveCount = 0;
    match_count = 0;
    for (int i = 0; i < records->count(); i++) {
        if (IS_RECORD(isSaveLayer)) {
            SkPaint* paint = isSaveLayer.get()->paint;

            // if this is the first save layer:
            //     push MatchOuter
            // if this is not the first save layer:
            //     if the current top state is MatchSave:
            //         bail: make the current top Ignore
            //         push MatchOuter
            //     else if the current top state is MatchBottom:
            //         if the save layer is a plain dstin one:
            //             push MatchDstIn
            //         else:
            //             bail: make the current top Ignore
            //             push MatchOuter
            //     else if the current top state is MatchDstIn or MatchDraw:
            //         bail: make the current top Ignore
            //             and also make the state beneath Ignore
            //         push MatchOuter
            //     else if the current top state is Matched:
            //         bail: make the current top Ignore
            //         push MatchOuter
            //     else:
            //         bail: make the current top Ignore
            //         push MatchOuter
            if (state_stack.empty()) {
                state_stack.push_back({
                        MatchState::MatchOuter,
                        i,
                        -1,
                        -1,
                        -1,
                        saveCount,
                        {},
                });
                continue;
            }

            if (state_stack.back().state == MatchState::MatchSave) {
                state_stack.back().state = MatchState::Ignore;
                state_stack.push_back({
                        MatchState::MatchOuter,
                        i,
                        -1,
                        -1,
                        -1,
                        saveCount,
                        {},
                });
                continue;
            }

            if (state_stack.back().state == MatchState::MatchBottom) {
                if (isPaintDstInMask(paint)) {
                    const int outerIndex = state_stack.back().outerIndex;
                    state_stack.push_back({
                            MatchState::MatchDstIn,
                            outerIndex,
                            i,
                            -1,
                            -1,
                            saveCount,
                            {},
                    });
                } else {
                    state_stack.back().state = MatchState::Ignore;
                    state_stack.push_back({
                            MatchState::MatchOuter,
                            i,
                            -1,
                            -1,
                            -1,
                            saveCount,
                            {},
                    });
                }
                continue;
            }

            if (state_stack.back().state == MatchState::MatchDstIn ||
                state_stack.back().state == MatchState::MatchDraw) {
                state_stack.back().state = MatchState::Ignore;
                SkASSERTF(state_stack.size() >= 2, "DstInToClip: expected outer state");
                state_stack[state_stack.size() - 2].state = MatchState::Ignore;
                state_stack.push_back({
                        MatchState::MatchOuter,
                        i,
                        -1,
                        -1,
                        -1,
                        saveCount,
                        {},
                });
                continue;
            }

            if (state_stack.back().state == MatchState::Matched) {
                state_stack.back().state = MatchState::Ignore;
                state_stack.push_back({
                        MatchState::MatchOuter,
                        i,
                        -1,
                        -1,
                        -1,
                        saveCount,
                        {},
                });
                continue;
            }

            state_stack.back().state = MatchState::Ignore;
            state_stack.push_back({
                    MatchState::MatchOuter,
                    i,
                    -1,
                    -1,
                    -1,
                    saveCount,
                    {},
            });

        } else if (IS_RECORD(isSave)) {
            saveCount += 1;
            // if the current state is MatchOuter:
            //    change the state to MatchSave
            if (!state_stack.empty() && state_stack.back().state == MatchState::MatchOuter) {
                state_stack.back().state = MatchState::MatchSave;
            }
        } else if (IS_RECORD(isConcat44)) {
            if (state_stack.empty()) {
                continue;
            }

            if (state_stack.back().state == MatchState::MatchDstIn ||
                state_stack.back().state == MatchState::MatchDraw) {
                state_stack.back().state = MatchState::Ignore;
                SkASSERTF(state_stack.size() >= 2, "DstInToClip: expected outer state");
                state_stack[state_stack.size() - 2].state = MatchState::Ignore;
            } else if (state_stack.back().state != MatchState::Ignore) {
                state_stack.back().state = MatchState::Ignore;
            }
        } else if (IS_RECORD(isRestore)) {
            // take care of the save restore pairs first
            if (state_stack.empty() || state_stack.back().saveCount < saveCount) {
                SkASSERTF(saveCount > 0, "unbalanced restore at command %d", i);
                saveCount -= 1;
                // If current state is MatchSave
                //    change it to MatchBottom
                if (!state_stack.empty() && state_stack.back().state == MatchState::MatchSave) {
                    state_stack.back().state = MatchState::MatchBottom;
                }
                continue;
            }

            // now we check if we matched the inner dstin mask
            if (state_stack.back().state == MatchState::MatchDraw) {
                // we pop the current state
                // then we change the new current state to Matched
                const MatchState innerState = state_stack.back();
                state_stack.pop_back();
                if (!state_stack.empty()) {
                    state_stack.back().state = MatchState::Matched;
                    state_stack.back().innerIndex = innerState.innerIndex;
                    state_stack.back().innerRestoreIndex = i;
                    state_stack.back().lastDrawIndex = innerState.lastDrawIndex;
                    state_stack.back().clipIndices = innerState.clipIndices;
                }
                continue;
            }
            // now we check if we matched the entire pattern
            else if (state_stack.back().state == MatchState::Matched) {
                const int insertAt = state_stack.back().outerIndex + 1;

                for (int clipIndex : state_stack.back().clipIndices) {
                    SkRecords::Is<SkRecords::ClipRect> clipRect;
                    const bool hasClip = records->mutate(clipIndex, clipRect);
                    if (!hasClip) {
                        continue;
                    }
                    const SkRecords::ClipRect* src = clipRect.get();
                    SkRecords::ClipRect* dst = records->insert<SkRecords::ClipRect>(insertAt);
                    new (dst) SkRecords::ClipRect{src->rect, src->opAA};
                }

                SkRecords::Is<SkRecords::DrawPath> drawPath;
                const bool hasDraw = records->mutate(state_stack.back().lastDrawIndex, drawPath);
                if (hasDraw) {
                    const SkRecords::DrawPath* src = drawPath.get();
                    SkRecords::ClipPath* dst = records->insert<SkRecords::ClipPath>(insertAt);
                    new (dst) SkRecords::ClipPath{
                            src->path,
                            SkRecords::ClipOpAndAA(SkClipOp::kIntersect, true),
                    };
                }

                for (int j = state_stack.back().innerIndex;
                     j <= state_stack.back().innerRestoreIndex;
                     j++) {
                    records->replace<SkRecords::NoOp>(j);
                }
                match_count += 1;
            }

            state_stack.pop_back();
        } else if (IS_RECORD(isDraw)) {
            // if the current state is MatchDstIn:
            //    change the state to MatchDraw
            // else if the current state is MatchDraw:
            //    bail: Ignore the current state and the one below it
            // else if the current state is Matched:
            //    bail: Ignore the current state
            if (state_stack.empty()) {
                continue;
            }

            if (state_stack.back().state == MatchState::MatchDstIn) {
                if (IS_RECORD(isDrawPath) && isPaintPlain(isDraw.get(), true)) {
                    state_stack.back().state = MatchState::MatchDraw;
                    state_stack.back().lastDrawIndex = i;
                } else {
                    state_stack.back().state = MatchState::Ignore;
                    SkASSERTF(state_stack.size() >= 2, "DstInToClip: expected outer state");
                    state_stack[state_stack.size() - 2].state = MatchState::Ignore;
                }
            } else if (state_stack.back().state == MatchState::MatchDraw) {
                state_stack.back().state = MatchState::Ignore;
                SkASSERTF(state_stack.size() >= 2, "DstInToClip: expected outer state");
                state_stack[state_stack.size() - 2].state = MatchState::Ignore;
            } else if (state_stack.back().state == MatchState::Matched) {
                state_stack.back().state = MatchState::Ignore;
            }
        } else if (IS_RECORD(isClipRect)) {
            if (state_stack.empty()) {
                continue;
            }
            if (state_stack.back().state == MatchState::MatchDstIn ||
                state_stack.back().state == MatchState::MatchDraw) {
                state_stack.back().clipIndices.push_back(i);
            }
        }
    }

    records->executeInsertions();
}
