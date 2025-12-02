#include <cstddef>
#include <cstdio>
#include <sstream>
#include <stack>
#include <string>
#include <tuple>
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkImage.h"
#include "include/core/SkImageInfo.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPixmap.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordPattern.h"
#include "src/core/SkRecords.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, ".", "Output directory");

bool isPaintPlain(SkPaint* paint, bool testForOpaque = true) {
    if (paint->getShader() || paint->getColorFilter() || paint->getImageFilter() ||
        paint->getMaskFilter()) {
        return false;
    }

    return (testForOpaque ? paint->getAlphaf() == 1.0 : true) && paint->isSrcOver();
}

struct RemoveOpaqueSaveLayers {
    std::stringstream log;
    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    SkRecords::Is<SkRecords::Save> isSave;
    SkRecords::Is<SkRecords::Restore> isRestore;
    SkRecords::IsSingleDraw isDraw;

    enum class MatchState { Matching, Ignore };
    std::stack<std::tuple<MatchState, int>> back_indices;

    void transform(SkRecord& records) {
        for (int i = 0; i < records.count(); i++) {
            if (records.mutate(i, isSaveLayer)) {
                back_indices.emplace(isPaintPlain(isSaveLayer.get()->paint) ? MatchState::Matching
                                                                            : MatchState::Ignore,
                                     i);
            } else if (records.mutate(i, isSave)) {
                back_indices.emplace(MatchState::Ignore, i);
            } else if (records.mutate(i, isDraw)) {
                if (std::get<0>(back_indices.top()) == MatchState::Ignore) continue;
                if (!isPaintPlain(isDraw.get())) {
                    auto [state, bi] = back_indices.top();
                    back_indices.emplace(MatchState::Ignore, bi);
                }
            } else if (records.mutate(i, isRestore)) {
                auto [state, bi] = back_indices.top();
                back_indices.pop();
                if (state == MatchState::Matching) {
                    records.replace<SkRecords::Save>(bi);
                    log << "Matched! SaveLayer @ " << bi << " and Restore @ " << i << '\n';
                }
            }
        }
    }

    std::string str() const { return log.str(); }
};

struct RecordPrinter {
    std::ostringstream os;
    int index = 0;

    template <typename T> void operator()(const T& op) {
        os << "    [" << index++ << "] " << typeid(T).name() << '\n';
    }

    std::string str() const { return os.str(); }
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
    std::string dataPath = outdir + "/report_data.txt";

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

    RecordPrinter printerBefore;
    for (int i = 0; i < records.count(); i++) {
        records.visit(i, printerBefore);
    }

    const int beforeCommandCount = records.count();
    const std::string beforeCommands = printerBefore.str();

    drawRecordToFile(records, bounds, beforePath.c_str());

    RemoveOpaqueSaveLayers logger;
    logger.transform(records);

    RecordPrinter printerAfter;
    for (int i = 0; i < records.count(); i++) {
        records.visit(i, printerAfter);
    }

    const int afterCommandCount = records.count();
    const std::string afterCommands = printerAfter.str();
    const std::string saveLayerLog = logger.str();

    drawRecordToFile(records, bounds, afterPath.c_str());

    FILE* dataFile = fopen(dataPath.c_str(), "w");
    if (!dataFile) {
        ERROR("Failed to open output file %s", dataPath.c_str());
        return 1;
    }

    fprintf(dataFile, "before_count:%d\n", beforeCommandCount);
    fprintf(dataFile, "after_count:%d\n", afterCommandCount);
    fprintf(dataFile, "-----BEGIN BEFORE COMMANDS-----\n%.*s-----END BEFORE COMMANDS-----\n",
            static_cast<int>(beforeCommands.size()), beforeCommands.c_str());
    fprintf(dataFile, "-----BEGIN AFTER COMMANDS-----\n%.*s-----END AFTER COMMANDS-----\n",
            static_cast<int>(afterCommands.size()), afterCommands.c_str());
    fprintf(dataFile, "-----BEGIN SAVE_LAYER_LOG-----\n%.*s-----END SAVE_LAYER_LOG-----\n",
            static_cast<int>(saveLayerLog.size()), saveLayerLog.c_str());
    fclose(dataFile);

    printf("Wrote report data to %s\n", dataPath.c_str());

    return 0;
}
