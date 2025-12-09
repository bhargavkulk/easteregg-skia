#ifndef EASTER_EGG_SKIA_EASTEREGG_H_
#define EASTER_EGG_SKIA_EASTEREGG_H_

#include <sstream>
#include <string>

#include "include/private/base/SkTArray.h"
#include "src/core/SkRecordPattern.h"

class SkPaint;
class SkRecord;

bool isPaintPlain(SkPaint* paint, bool testForOpaque = true);

struct RemoveOpaqueSaveLayers {
    void transform(SkRecord& records);
    std::string str() const;

private:
    enum class MatchState { Matching, Ignore };

    void dbg();

    std::stringstream log;
    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::Is<SkRecords::Restore> isRestore;
    SkRecords::IsSingleDraw isDraw;
    skia_private::STArray<8, MatchState> state_stack;
    skia_private::STArray<8, int> index_stack;
};

#endif  // EASTER_EGG_SKIA_EASTEREGG_H_
