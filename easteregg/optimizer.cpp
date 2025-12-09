#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include "include/core/SkCanvas.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkStream.h"
#include "include/private/base/SkTArray.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "src/core/SkRecordPattern.h"
#include "src/core/SkRecords.h"
#include "tools/flags/CommandLineFlags.h"

#ifdef DEBUG
#define DPRINT(x) std::cout << x << std::endl
#else
#define DPRINT(x)
#endif

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "optimized.skp", "Output .skp file");
static DEFINE_string(transform, "easteregg", "Transform to run: easteregg, skrecordopt, or none");

bool isPaintPlain(SkPaint* paint, bool testForOpaque = true) {
    if (!paint) {
        return true;
    }

    if (paint->getShader() || paint->getColorFilter() || paint->getImageFilter() ||
        paint->getMaskFilter()) {
        return false;
    }

    return (testForOpaque ? paint->getAlphaf() == 1.0 : true) && paint->isSrcOver();
}

struct RecordPrinter {
    std::ostringstream os;
    int index = 0;

    template <typename T> void operator()(const T& op) {
        os << "    [" << index++ << "] " << typeid(T).name() << "<br />\n";
    }

    std::string str() { return os.str(); }
};

struct RemoveOpaqueSaveLayers {
    std::stringstream log;
    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::Is<SkRecords::Restore> isRestore;
    SkRecords::IsSingleDraw isDraw;

    enum class MatchState { Matching, Ignore };
    skia_private::STArray<8, MatchState> state_stack;
    skia_private::STArray<8, int> index_stack;

    void dbg() {
        std::ostringstream dbgStream;
        for (int i = 0; i < index_stack.size(); ++i) {
            dbgStream << ((state_stack[i] == MatchState::Matching) ? "Match " : "Ignore ")
                      << index_stack[i] << ", ";
        }
        DPRINT(dbgStream.str());
    }

    void transform(SkRecord& records) {
        for (int i = 0; i < records.count(); i++) {
            if (records.mutate(i, isSaveLayer)) {
                state_stack.push_back(isPaintPlain(isSaveLayer.get()->paint) ? MatchState::Matching
                                                                             : MatchState::Ignore);
                index_stack.push_back(i);
            } else if (records.mutate(i, isSave)) {
                state_stack.push_back(MatchState::Ignore);
                index_stack.push_back(i);
            } else if (records.mutate(i, isDraw)) {
                if (state_stack.empty() || state_stack.back() == MatchState::Ignore) continue;
                if (!isPaintPlain(isDraw.get(), false)) {
                    state_stack.back() = MatchState::Ignore;
                }
            } else if (records.mutate(i, isRestore)) {
                if (state_stack.empty()) continue;
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

    std::string str() const { return log.str(); }
};

sk_sp<SkPicture> PictureFromRecord(const SkRecord& records, const SkRect& bounds) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(bounds);
    if (!canvas) {
        return nullptr;
    }
    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);
    return recorder.finishRecordingAsPicture();
}

bool writePictureToSkp(const sk_sp<SkPicture>& picture, const std::string& path) {
    if (!picture) {
        return false;
    }
    SkFILEWStream stream(path.c_str());
    if (!stream.isValid()) return false;
    picture->serialize(&stream);
    return true;
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        ERROR("Must specify --input");
        return 1;
    }

    SkFILEStream stream(FLAGS_input[0]);
    if (!stream.isValid()) {
        ERROR("Failed to read file %s", FLAGS_input[0]);
        return 1;
    }

    const std::string outputPath = FLAGS_output[0];

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
    if (!picture) {
        ERROR("Error loading skp from %s", FLAGS_input[0]);
        return 1;
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);

    picture->playback(&recorder);

    DPRINT("Record has " << records.count() << " commands.");

    const std::string transform = FLAGS_transform[0];

    if (transform == "easteregg") {
        RemoveOpaqueSaveLayers opt;
        opt.transform(records);
        DPRINT("RemoveOpaqueSaveLayers transform applied");

        auto optimizedPicture = PictureFromRecord(records, bounds);
        if (!writePictureToSkp(optimizedPicture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
        DPRINT("Optimized SKP written to " << outputPath);
    } else if (transform == "skrecordopt") {
        SkRecordOptimize(&records);
        DPRINT("SkRecordOptimize transform applied");

        auto optimizedPicture = PictureFromRecord(records, bounds);
        if (!writePictureToSkp(optimizedPicture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
        DPRINT("Optimized SKP written to " << outputPath);
    } else if (transform == "none") {
        if (!writePictureToSkp(picture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
        DPRINT("No optimization applied; SKP copied to " << outputPath);
    } else {
        ERROR("Unknown transform '%s'", transform.c_str());
        return 1;
    }

    return 0;
}
