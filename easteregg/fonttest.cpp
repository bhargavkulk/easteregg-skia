#include "include/core/SkCanvas.h"
#include "include/core/SkData.h"
#include "include/core/SkFont.h"
#include "include/core/SkFontMgr.h"
#include "include/core/SkImage.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkSurface.h"
#include "include/core/SkStream.h"
#include "include/core/SkTypeface.h"
#include "include/encode/SkPngEncoder.h"
#include "include/ports/SkFontMgr_mac_ct.h"
#include "tools/flags/CommandLineFlags.h"

#include <cstdio>
#include <cstring>

static DEFINE_string(font, "", "Input .otf/.ttf font file path");
static DEFINE_string(output, "out.png", "Output .png file path");
static DEFINE_string(skp, "", "Optional output .skp file path");

int main(int argc, char** argv) {
    CommandLineFlags::SetUsage("Renders sample text using a font file");
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_font.isEmpty()) {
        fprintf(stderr, "Error: Must specify --font\n");
        return 2;
    }

    auto data = SkData::MakeFromFileName(FLAGS_font[0]);
    if (!data) return -1;

    auto fontMgr = SkFontMgr_New_CoreText(nullptr);
    if (!fontMgr) return -1;

    sk_sp<SkTypeface> face = fontMgr->makeFromData(data);
    if (!face) return -1;

    const SkImageInfo info = SkImageInfo::MakeN32Premul(1024, 256);
    auto surface = SkSurfaces::Raster(info);
    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorWHITE);

    SkPaint paint;
    paint.setAntiAlias(true);

    SkFont font(face, 100);
    font.setEdging(SkFont::Edging::kAntiAlias);

    const char* text = "Skia SVG Test";
    SkPictureRecorder recorder;
    SkCanvas* recordCanvas = recorder.beginRecording(SkRect::MakeIWH(info.width(), info.height()));
    recordCanvas->clear(SK_ColorWHITE);
    recordCanvas->drawSimpleText(text, strlen(text), SkTextEncoding::kUTF8, 20, 150, font, paint);
    sk_sp<SkPicture> picture = recorder.finishRecordingAsPicture();
    if (!picture) return -1;

    picture->playback(canvas);

    auto img = surface->makeImageSnapshot();
    SkFILEWStream out(FLAGS_output[0]);
    SkPixmap pixmap;
    if (!img->peekPixels(&pixmap)) return -1;
    SkPngEncoder::Options options;
    if (!SkPngEncoder::Encode(&out, pixmap, options)) return -1;

    if (!FLAGS_skp.isEmpty()) {
        SkFILEWStream skpOut(FLAGS_skp[0]);
        if (!skpOut.isValid()) return -1;
        picture->serialize(&skpOut);
    }
    return 0;
}
