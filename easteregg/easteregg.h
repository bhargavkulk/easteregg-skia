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
    void transform(SkRecord* records);

private:
    enum class MatchState { Matching, Ignore };

    void dbg();

    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::Is<SkRecords::Restore> isRestore;
    SkRecords::IsSingleDraw isDraw;
    skia_private::STArray<8, MatchState> state_stack;
    skia_private::STArray<8, int> index_stack;
};

// * λskia
// (rewrite (SaveLayer (Draw (Empty) shape (Paint (Color a r g b) (SrcOver) style (IdFilter) i1) clip transform)
//                     (Draw (Empty) shape (Paint (LinearGradient true) (SrcOver) style (IdFilter) i2) clip transform)
//                     (Paint (Color 1.0 r1 g1 b1) (DstIn) nostyle (IdFilter) i3))
//          (Draw (Empty) shape (Paint (Color a r g b) (SrcOver) style (IdFilter) i1) clip transform)
//          :ruleset opt)
//
// Observations: If the layer under bottom is Empty, then the immediate preceeding command has to
//               either be a SaveLayer or nothing (the draw is the first command of the program)
// Assumptions: The clips (and transforms) are the same. Given how these match rules exist in our
//              benchmarks, I think this is always true? (λskia also simplifies clips, but again
//              what I think is that even if we dont simplify we can assume they are the same. These
//              assumptions weaken the correctness claim. BUT, it also hard to implement math as is
//              in code.)
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
    void transform(SkRecord& records);

private:
    enum class MatchState { Matching, Ignore };

    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::IsSingleDraw isDraw;
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
    void transform(SkRecord* records);
    void operator()(SkRecord* records) { transform(records); }

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

    skia_private::STArray<8, MatchState> state_stack;

    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::Is<SkRecords::Restore> isRestore;
    SkRecords::IsSingleDraw isDraw;
};

#endif  // EASTER_EGG_SKIA_EASTEREGG_H_
