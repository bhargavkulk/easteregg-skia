#ifndef EASTER_EGG_SKIA_EASTEREGG_H_
#define EASTER_EGG_SKIA_EASTEREGG_H_

#include "include/private/base/SkTArray.h"
#include "src/core/SkRecordPattern.h"
#include "src/core/SkRecords.h"

class SkPaint;
class SkRecord;

bool isPaintPlain(SkPaint* paint, bool testForOpaque = true);

struct RemoveOpaqueSaveLayers {
    void operator()(SkRecord* records);
    void transform(SkRecord* records) const;
    int matchCount() const { return match_count; }

private:
    enum class MatchState { Matching, Ignore };
    mutable skia_private::STArray<8, MatchState> state_stack;
    mutable skia_private::STArray<8, int> index_stack;

    void dbg();

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;
};

struct CopyRemoveOpaqueSaveLayer {
    void operator()(SkRecord* records) const;
    void transform(SkRecord* records) const;
    int matchCount() const { return match_count; }

private:
    struct MatchState {
        enum {
            Matching,
            Ignore,
        } state;
        int index;
        int saveCount;
    };
    mutable skia_private::STArray<8, MatchState> state_stack;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;
};

// * λskia
// (rewrite (SaveLayer (Draw (Empty) shape (Paint (Color a r g b) (SrcOver) style (IdFilter) i1) clip transform')
//                     (Draw (Empty) shape (Paint (LinearGradient true) (SrcOver) style (IdFilter) i2) clip transform)
//                     (Paint (Color 1.0 r1 g1 b1) (DstIn) nostyle (IdFilter) i3))
//          (Draw (Empty) shape (Paint (Color a r g b) (SrcOver) style (IdFilter) i1) clip transform)
//          :ruleset opt)
//
// Observations: If the layer under bottom is Empty, then the immediate preceeding command has to
//               either be a SaveLayer or nothing (the draw is the first command of the program)
// * Skia
// SaveLayer:
//   Draw shape solidfill idfilter
//   SaveLayer 1.0 DstIn:
//     Draw shape Linear/RadialGradient(opaque=true) srcover idfilter
// --->
// SaveLayer:
//   Draw shape solidfill idfilter
//   NoOp
//   NoOp

struct GradientDstInToMasks {
    void transform(SkRecord* records) const;
    int matchCount() const { return match_count; }

private:
    struct MatchState {
        enum {
            OuterLayer,
            OuterFill,
            MaskLayer,
            MaskFill,
            Ignore,
        } state;
        int saveLayerIndex;
        int saveCount;
        SkPaint* paint;
    };

    mutable skia_private::STArray<8, MatchState> state_stack;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;
};

// * λskia
// (rewrite (SaveLayer (Empty)
//                     (Draw (Empty) shape (Paint (Color 1.0 1.0 1.0 1.0) (SrcOver) style (IdFilter) i1) clip transform)
//                     (Paint (Color 1.0 r g b) (SrcOver) nostyle (LumaFilter) i2))
//          (Draw (Empty) shape (Paint (Color 1.0 0.0 0.0 0.0) (SrcOver) style (IdFilter) i1) clip transform)
//          :ruleset opt)
//
// Observation: Empty as bot indidicates these are 2 save layers next to each
// other, or its the first save layer in a program
// Assumptions: None! should be an easy win
// * Skia
// SaveLayer:
//   SaveLayer Luma:
//     Draw (Color white)
// --->
// SaveLayer:
//   Save:
//     Draw (Color black)

struct RemoveLoneLuma {
    void transform(SkRecord* records) const;
    void operator()(SkRecord* records) const { transform(records); }
    int matchCount() const { return match_count; }

private:
    struct MatchState {
        enum {
            MatchSaveLayer,
            MatchDraw,
            Ignore,
        } state;
        int index;
        int saveCount;
        int ptr;
        SkPaint* paint;
    };

    mutable skia_private::STArray<8, MatchState> state_stack;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;
};

struct DstInToClip {
    void transform(SkRecord* records) const;
    void operator()(SkRecord* records) const { transform(records); }
    int matchCount() const { return match_count; }

private:
    struct MatchState {
        enum {
            Ignore,
            MatchOuter,
            MatchSave,
            MatchDstIn,
            MatchDraw,
            Matched,
            MatchBottom,
        } state;
        int outerIndex;
        int innerIndex;
        int innerRestoreIndex;
        int lastDrawIndex;
        int saveCount;
        skia_private::STArray<8, int> clipIndices;
    };

    mutable skia_private::STArray<8, MatchState> state_stack;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::Is<SkRecords::Concat44> isConcat44;
    mutable SkRecords::Is<SkRecords::ClipRect> isClipRect;
    mutable SkRecords::Is<SkRecords::DrawPath> isDrawPath;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;
};

template <typename Derived, typename State> class SkOptPass {
protected:
    struct Frame {
        int layerIndex;
        int saveCountAtOpen;
    };
    mutable skia_private::STArray<8, Frame> frame_stack;
    mutable skia_private::STArray<8, State> state_stack;
    mutable int save_count = 0;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::IsSingleDraw isDraw;

public:
    void run(SkRecord* r) const {
        frame_stack.reset(0);
        state_stack.reset(0);
        save_count = 0;
        auto& self = *static_cast<const Derived*>(this);

        for (int i = 0; i < r->count(); ++i) {
            if (r->mutate(i, isSaveLayer)) {
                frame_stack.push_back({i, save_count});
                state_stack.push_back(State{});  // default only
                self.onSaveLayer(
                        r, i, isSaveLayer.get(), &state_stack.back(),
                        state_stack.size() >= 2 ? &state_stack[state_stack.size() - 2] : nullptr,
                        &frame_stack.back());
            } else if (r->mutate(i, isSave)) {
                save_count += 1;
                self.onSave(r, i, state_stack.empty() ? nullptr : &state_stack.back());
            } else if (r->mutate(i, isRestore)) {
                if (frame_stack.empty() || frame_stack.back().saveCountAtOpen < save_count) {
                    SkASSERTF(save_count > 0, "unbalanced restore at command %d", i);
                    save_count -= 1;
                    self.onRestoreNormal(r, i, state_stack.empty() ? nullptr : &state_stack.back());
                    continue;
                }

                self.onRestoreLayer(r, i, &state_stack.back(), &frame_stack.back());
                frame_stack.pop_back();
                state_stack.pop_back();
            } else if (r->mutate(i, isDraw)) {
                if (state_stack.empty()) {
                    continue;
                }
                if (frame_stack.back().saveCountAtOpen < save_count) {
                    self.onDraw(r, i, isDraw.get(), &state_stack.back(), true);
                } else {
                    self.onDraw(r, i, isDraw.get(), &state_stack.back(), false);
                }
            } else {
                self.onOther(r, i, state_stack.empty() ? nullptr : &state_stack.back());
            }
        }
    }
};

struct NewRemoveOpaqueSaveLayersState {
    enum class Phase { Matching, Ignore };
    Phase phase = Phase::Ignore;
};

struct NewRemoveOpaqueSaveLayers
        : SkOptPass<NewRemoveOpaqueSaveLayers, NewRemoveOpaqueSaveLayersState> {
    using Base = SkOptPass<NewRemoveOpaqueSaveLayers, NewRemoveOpaqueSaveLayersState>;
    using State = NewRemoveOpaqueSaveLayersState;
    using Phase = NewRemoveOpaqueSaveLayersState::Phase;
    using Frame = Base::Frame;
    void transform(SkRecord* records) const {
        match_count = 0;
        this->run(records);
    }
    void operator()(SkRecord* records) const { this->transform(records); }
    int matchCount() const { return match_count; }

    void onSaveLayer(
            SkRecord*, int, const SkRecords::SaveLayer* sl, State* cur, State* parent,
            const Frame*) const {
        if (parent) {
            parent->phase = Phase::Ignore;
        }
        cur->phase = isPaintPlain(sl->paint) ? Phase::Matching : Phase::Ignore;
    }

    void onSave(SkRecord*, int, State*) const {}

    void onDraw(SkRecord*, int, SkPaint* p, State* cur, bool insideSaveScope) const {
        if (insideSaveScope) {
            return;
        }
        if (cur && cur->phase == Phase::Matching && !isPaintPlain(p, false))
            cur->phase = Phase::Ignore;
    }
    void onRestoreLayer(SkRecord* r, int, State* cur, const Frame* frame) const {
        if (cur && cur->phase == Phase::Matching) {
            r->replace<SkRecords::Save>(frame->layerIndex);
            match_count += 1;
        }
    }
    void onRestoreNormal(SkRecord*, int, State*) const {}
    void onOther(SkRecord*, int, State*) const {}

private:
    mutable int match_count = 0;
};

#endif  // EASTER_EGG_SKIA_EASTEREGG_H_
