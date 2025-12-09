#include "easteregg/easteregg.h"

#include <iostream>

#include "include/core/SkPaint.h"
#include "src/core/SkRecord.h"

#ifdef DEBUG
#define DPRINT(x) std::cout << x << std::endl
#else
#define DPRINT(x)
#endif

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

void RemoveOpaqueSaveLayers::dbg() {
    std::ostringstream dbgStream;
    for (int i = 0; i < index_stack.size(); ++i) {
        dbgStream << ((state_stack[i] == MatchState::Matching) ? "Match " : "Ignore ")
                  << index_stack[i] << ", ";
    }
    DPRINT(dbgStream.str());
}

void RemoveOpaqueSaveLayers::transform(SkRecord& records) {
    for (int i = 0; i < records.count(); i++) {
        if (records.mutate(i, isSaveLayer)) {
            state_stack.push_back(isPaintPlain(isSaveLayer.get()->paint) ? MatchState::Matching
                                                                         : MatchState::Ignore);
            index_stack.push_back(i);
        } else if (records.mutate(i, isSave)) {
            state_stack.push_back(MatchState::Ignore);
            index_stack.push_back(i);
        } else if (records.mutate(i, isDraw)) {
            if (state_stack.empty() || state_stack.back() == MatchState::Ignore) {
                continue;
            }
            if (!isPaintPlain(isDraw.get(), false)) {
                state_stack.back() = MatchState::Ignore;
            }
        } else if (records.mutate(i, isRestore)) {
            if (state_stack.empty()) {
                continue;
            }
            auto state = state_stack.back();
            auto index = index_stack.back();
            state_stack.pop_back();
            index_stack.pop_back();

            if (state == MatchState::Matching) {
                records.replace<SkRecords::Save>(index);
            }
        }
    }
}

std::string RemoveOpaqueSaveLayers::str() const {
    return log.str();
}
