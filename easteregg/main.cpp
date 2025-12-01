#include <cstdio>
#include <sstream>
#include <vector>
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkImage.h"
#include "include/core/SkImageInfo.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPixmap.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecords.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, ".", "Output directory");

// Loops through the SkRecord searching for SaveLayers. When a SaveLayer is
// seen, push its index on to the back_indices vector. Also log it in the
// stringstream. When a restore is seen pop the index from back_indices and
// then log which index the restore points to along with its own index in
// the string stream.
template <typename Command> struct CommandDetector {
    bool matched = false;
    void operator()(const Command&) { matched = true; }
    template <typename T> void operator()(const T&) {}
};

struct RemoveOpaqueSaveLayers {
    std::vector<size_t> back_indices;
    std::ostringstream log;

    void transform(SkRecord& record) {
        back_indices.clear();
        log.str("");
        log.clear();

        for (int i = 0; i < record.count(); ++i) {
            CommandDetector<SkRecords::SaveLayer> saveDetector;
            record.visit(i, saveDetector);
            if (saveDetector.matched) {
                back_indices.push_back(i);
                log << "SaveLayer[" << i << "]\n";
                continue;
            }

            CommandDetector<SkRecords::Restore> restoreDetector;
            record.visit(i, restoreDetector);
            if (restoreDetector.matched) {
                if (back_indices.empty()) {
                    log << "Restore[" << i << "] has no matching SaveLayer\n";
                    continue;
                }
                const size_t saveLayerIndex = back_indices.back();
                back_indices.pop_back();
                log << "Restore[" << i << "] -> SaveLayer[" << saveLayerIndex << "]\n";
            }
        }
    }

    std::string str() const { return log.str(); }
};

struct RecordPrinter {
    std::ostringstream os;
    int index = 0;

    template <typename T> void operator()(const T& op) {
        os << "    [" << index++ << "] " << typeid(T).name() << "<br />\n";
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
    std::string htmlPath = outdir + "/index.html";

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

    RecordPrinter printer;
    for (int i = 0; i < records.count(); i++) {
        records.visit(i, printer);
    }

    const int beforeCommandCount = records.count();

    drawRecordToFile(records, bounds, beforePath.c_str());

    RemoveOpaqueSaveLayers logger;
    logger.transform(records);

    FILE* outFile = fopen(htmlPath.c_str(), "w");
    if (!outFile) {
        ERROR("Failed to open output file %s", FLAGS_output[0]);
        return 1;
    }

    fprintf(outFile, "<!DOCTYPE html>\n");
    fprintf(outFile, "<html><head><title>SKP Comparison</title></head><body>\n");
    fprintf(outFile, "<h1>Record Commands (%d total)</h1>\n", beforeCommandCount);
    fprintf(outFile, "<pre>%s</pre>\n", printer.str().c_str());
    fprintf(outFile, "<h1>SaveLayer / Restore Log</h1>\n");
    fprintf(outFile, "<pre>%s</pre>\n", logger.str().c_str());
    fprintf(outFile, "<h1>Record Snapshot</h1>\n");
    fprintf(outFile, "<img src='before.png' />\n");
    fprintf(outFile, "</body></html>\n");

    fclose(outFile);

    return 0;
}
