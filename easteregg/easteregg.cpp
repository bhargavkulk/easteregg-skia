#include "easteregg/easteregg.h"

#include "include/core/SkColor.h"
#include "include/core/SkPaint.h"
#include "include/private/base/SkDebug.h"
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
            }
        }
    }
}

void GradientDstInToMasks::transform(SkRecord* records) const {
    int saveCount = 0;
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
                records->replace<SkRecords::SaveLayer>(state_stack.back().index);
                state_stack.back().paint->setColor4f(SkColors::kBlack);
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
