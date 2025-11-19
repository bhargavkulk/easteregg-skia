#include "include/core/SkCanvas.h"
#include "include/core/SkImage.h"
#include "include/core/SkPicture.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "tools/flags/CommandLineFlags.h"

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "output.png", "Output PNG file");

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        SkDebugf("Must specify --input\n");
        return 1;
    }

    SkFILEStream stream(FLAGS_input[0]);
    if (!stream.isValid()) {
        SkDebugf("Failed to open %s\n", FLAGS_input[0]);
        return 1;
    }

    sk_sp<SkPicture> picture = SkPicture::MakeFromStream(&stream);
    if (!picture) {
        SkDebugf("Failed to deserialize picture\n");
        return 1;
    }

    SkRect bounds = picture->cullRect();
    auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(bounds.width(), bounds.height()));

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorWHITE);
    canvas->drawPicture(picture);

    sk_sp<SkImage> image = surface->makeImageSnapshot();
    SkPixmap pixmap;
    image->peekPixels(&pixmap);

    SkFILEWStream outStream(FLAGS_output[0]);
    SkPngEncoder::Encode(&outStream, pixmap, {});

    return 0;
}
