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
        // DSTIN CONCAT DEBUG: Track the net inner-mask transform so we can
        // tolerate cancelling concats and still bail on non-cancelling ones.
        SkM44 innerConcat = SkM44();
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

template <typename MatchState> struct SkOptPass {
    struct Frame {
        MatchState match_state;
        int save_count;
    };

    virtual ~SkOptPass() = default;

    mutable skia_private::STArray<8, Frame> frames;

    mutable SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    mutable SkRecords::Is<SkRecords::Save> isSave;
    mutable SkRecords::Is<SkRecords::Restore> isRestore;
    mutable SkRecords::Is<SkRecords::Concat44> isConcat44;
    mutable SkRecords::Is<SkRecords::ClipRect> isClipRect;
    mutable SkRecords::Is<SkRecords::DrawPath> isDrawPath;
    mutable SkRecords::IsSingleDraw isDraw;
    mutable int match_count = 0;

    void transform(SkRecord* records) const;
    void operator()(SkRecord* records) const { transform(records); }
    int matchCount() const { return match_count; }

    virtual MatchState onSaveLayer(SkRecord* records,
                                   int index,
                                   SkRecords::Is<SkRecords::SaveLayer> saveLayerMatch) const = 0;
    virtual void onSave(SkRecord* records, int index) const = 0;
    virtual void onRestore(SkRecord* records, int index) const = 0;
    virtual void onDraw(SkRecord* records, int index, SkRecords::IsSingleDraw& drawMatch) const = 0;
    virtual void onOther(SkRecord* records, int index) const = 0;
};

template <typename MatchState>
void SkOptPass<MatchState>::transform(SkRecord* records) const {
    frames.clear();

    int save_count = 0;
    for (int i = 0; i < records->count(); i++) {
        if (records->mutate(i, isSaveLayer)) {
            MatchState state = onSaveLayer(records, i, isSaveLayer);
            Frame frame;
            frame.match_state = state;
            frame.save_count = save_count;
            frames.push_back(frame);
        } else if (records->mutate(i, isSave)) {
            save_count += 1;
            onSave(records, i);
        } else if (records->mutate(i, isRestore)) {
            if (frames.empty()) {
                SkASSERTF(save_count > 0, "unbalanced restore at command %d", i);
                save_count -= 1;
                continue;
            }
            if (frames.back().save_count < save_count) {
                save_count -= 1;
                continue;
            }
            onRestore(records, i);
            frames.pop_back();
        } else if (records->mutate(i, isDraw)) {
            onDraw(records, i, isDraw);
        } else {
            onOther(records, i);
        }
    }
}

struct RemoveOpaqueSaveLayerPassMatchState {
    enum Kind {
        Matching,
        Ignore,
    } kind = Kind::Ignore;
    int save_layer_index = -1;
};

struct RemoveOpaqueSaveLayerPass : SkOptPass<RemoveOpaqueSaveLayerPassMatchState> {
    using MatchState = RemoveOpaqueSaveLayerPassMatchState;
    using SkOptPass<MatchState>::matchCount;
    using SkOptPass<MatchState>::operator();
    using SkOptPass<MatchState>::transform;

private:
    MatchState onSaveLayer(SkRecord* records,
                           int index,
                           SkRecords::Is<SkRecords::SaveLayer> saveLayerMatch) const override;
    void onSave(SkRecord* records, int index) const override;
    void onRestore(SkRecord* records, int index) const override;
    void onDraw(SkRecord* records, int index, SkRecords::IsSingleDraw& drawMatch) const override;
    void onOther(SkRecord* records, int index) const override;
};

using NewRemoveOpaqueSaveLayers = RemoveOpaqueSaveLayerPass;

#endif  // EASTER_EGG_SKIA_EASTEREGG_H_
