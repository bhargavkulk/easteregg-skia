#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include "include/core/SkCanvas.h"
#include "include/core/SkImage.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPicture.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "include/private/base/SkTArray.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "src/core/SkRecordPattern.h"
#include "src/core/SkRecords.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, ".", "Output directory");
static DEFINE_string(transform,
                     "easteregg",
                     "Transform to run: easteregg or skrecordopt");

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

struct RecordOutPrinter {
    int index = 0;

    template <typename T> void operator()(const T& op) {
        std::cout << "    [" << index++ << "] " << typeid(T).name() << "<br />\n";
    }
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
        for (int i = 0; i < index_stack.size(); ++i) {
            std::cout << ((state_stack[i] == MatchState::Matching) ? "Match " : "Ignore ")
                      << index_stack[i] << ", ";
        }
    }

    long long transform(SkRecord& records) {
        auto start = std::chrono::high_resolution_clock::now();
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
        auto end = std::chrono::high_resolution_clock::now();
        return std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    }

    std::string str() const { return log.str(); }
};

bool drawRecordToFile(const SkRecord& records, const SkRect& bounds, const char* filename) {
    auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(bounds.width(), bounds.height()));

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorWHITE);
    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);

    sk_sp<SkImage> image = surface->makeImageSnapshot();
    SkPixmap pixmap;
    image->peekPixels(&pixmap);

    SkFILEWStream stream(filename);
    if (!stream.isValid()) return false;
    SkPngEncoder::Encode(&stream, pixmap, {});
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

    std::string outdir = FLAGS_output[0];
    std::string beforePath = outdir + "/before.png";
    std::string afterPath = outdir + "/after.png";

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
    if (!picture) {
        ERROR("Error loading skp from %s", FLAGS_input[0]);
        return 1;
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);

    picture->playback(&recorder);

    printf("Record has %d commands.\n\n", records.count());

    drawRecordToFile(records, bounds, beforePath.c_str());

    const std::string transform = FLAGS_transform[0];

    if (transform == "easteregg") {
        RemoveOpaqueSaveLayers logger;
        const long long customDurationNs = logger.transform(records);
        std::cout << "RemoveOpaqueSaveLayers elapsed " << customDurationNs << " ns\n";

        drawRecordToFile(records, bounds, afterPath.c_str());
    } else if (transform == "skrecordopt") {
        SkRecord optimizeRecord;
        SkRecordCanvas optimizeRecorder(&optimizeRecord, bounds);
        picture->playback(&optimizeRecorder);
        const auto optimizeStart = std::chrono::high_resolution_clock::now();
        SkRecordOptimize(&optimizeRecord);
        const auto optimizeEnd = std::chrono::high_resolution_clock::now();
        const long long optimizeDurationNs =
                std::chrono::duration_cast<std::chrono::nanoseconds>(optimizeEnd - optimizeStart)
                        .count();
        std::cout << "SkRecordOptimize elapsed " << optimizeDurationNs << " ns\n";
    } else {
        ERROR("Unknown transform '%s'", transform.c_str());
        return 1;
    }

    return 0;
}
