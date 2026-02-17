#include <filesystem>
#include <string>
#include <vector>

#include "include/core/SkBlendMode.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkFont.h"
#include "include/core/SkM44.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPath.h"
#include "include/core/SkPathBuilder.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkRect.h"
#include "include/core/SkStream.h"
#include "tools/flags/CommandLineFlags.h"

static DEFINE_string(output_dir, "unit_skps", "Directory where generated .skp files are written");
static DEFINE_string(only, "", "Optional single case name to generate");

namespace {

void draw_unit__ClipLayer(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkRect bounds0 = SkRect::MakeLTRB(2.0f, 1.0f, 18.0f, 21.0f);
    canvas->saveLayer(&bounds0, nullptr);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(2.0f, 1.0f, 18.0f, 21.0f), SkClipOp::kIntersect, true);
    SkPathBuilder pathBuilder0;
    pathBuilder0.setFillType(SkPathFillType::kEvenOdd);
    pathBuilder0.moveTo(9.99999f, 1.74286f);
    pathBuilder0.cubicTo(9.92916f, 1.74286f, 9.85916f, 1.74369f, 9.78833f, 1.74536f);
    pathBuilder0.cubicTo(5.85416f, 1.85453f, 2.58416f, 5.14869f, 2.50166f, 9.08286f);
    pathBuilder0.cubicTo(2.44999f, 11.5404f, 3.58666f, 13.7304f, 5.36999f, 15.1337f);
    pathBuilder0.cubicTo(5.52166f, 15.2529f, 5.63166f, 15.4162f, 5.67333f, 15.6045f);
    pathBuilder0.lineTo(6.30416f, 18.447f);
    pathBuilder0.cubicTo(6.51583f, 19.3987f, 7.36083f, 20.0762f, 8.33583f, 20.0762f);
    pathBuilder0.lineTo(11.6617f, 20.0762f);
    pathBuilder0.cubicTo(12.6383f, 20.0762f, 13.4842f, 19.3987f, 13.6958f, 18.4445f);
    pathBuilder0.lineTo(14.3275f, 15.602f);
    pathBuilder0.cubicTo(14.3692f, 15.4154f, 14.4775f, 15.2537f, 14.6275f, 15.1354f);
    pathBuilder0.cubicTo(16.3733f, 13.7629f, 17.5f, 11.637f, 17.5f, 9.24286f);
    pathBuilder0.cubicTo(17.5f, 5.10036f, 14.1425f, 1.74286f, 9.99999f, 1.74286f);
    pathBuilder0.close();
    pathBuilder0.moveTo(10.0003f, 3.40939f);
    pathBuilder0.cubicTo(13.2161f, 3.40939f, 15.8336f, 6.02606f, 15.8336f, 9.24273f);
    pathBuilder0.cubicTo(15.8336f, 11.0386f, 15.0186f, 12.7086f, 13.5978f, 13.8252f);
    pathBuilder0.cubicTo(13.1428f, 14.1827f, 12.8244f, 14.6852f, 12.7011f, 15.2402f);
    pathBuilder0.lineTo(12.0686f, 18.0827f);
    pathBuilder0.cubicTo(12.0269f, 18.2752f, 11.8586f, 18.4094f, 11.6619f, 18.4094f);
    pathBuilder0.lineTo(8.33609f, 18.4094f);
    pathBuilder0.cubicTo(8.14109f, 18.4094f, 7.97359f, 18.2761f, 7.93192f, 18.0852f);
    pathBuilder0.lineTo(7.30025f, 15.2427f);
    pathBuilder0.cubicTo(7.17609f, 14.6869f, 6.85775f, 14.1827f, 6.40109f, 13.8236f);
    pathBuilder0.cubicTo(4.94359f, 12.6769f, 4.12942f, 10.9619f, 4.16859f, 9.11773f);
    pathBuilder0.cubicTo(4.23192f, 6.05523f, 6.77442f, 3.49606f, 9.83442f, 3.41189f);
    pathBuilder0.cubicTo(9.88942f, 3.41023f, 9.94525f, 3.40939f, 10.0003f, 3.40939f);
    pathBuilder0.close();
    SkPath path0 = pathBuilder0.detach();
    SkPaint paint0;
    paint0.setAntiAlias(true);
    paint0.setColor(SkColorSetARGB(255, 255, 255, 255));
    canvas->drawPath(path0, paint0);
    SkPathBuilder pathBuilder1;
    pathBuilder1.setFillType(SkPathFillType::kWinding);
    pathBuilder1.moveTo(10.0f, 6.81299f);
    pathBuilder1.lineTo(8.81253f, 9.18726f);
    pathBuilder1.lineTo(11.1875f, 9.18726f);
    pathBuilder1.lineTo(9.99952f, 11.561f);
    SkPath path1 = pathBuilder1.detach();
    SkPaint paint1;
    paint1.setAntiAlias(true);
    paint1.setColor(SkColorSetARGB(255, 255, 255, 255));
    paint1.setStyle(SkPaint::kStroke_Style);
    paint1.setStrokeWidth(1.6f);
    paint1.setStrokeCap(SkPaint::kRound_Cap);
    paint1.setStrokeJoin(SkPaint::kRound_Join);
    canvas->drawPath(path1, paint1);
    canvas->restore();
    SkRect bounds1 = SkRect::MakeLTRB(2.0f, 1.0f, 18.0f, 21.0f);
    SkPaint layerPaint1;
    layerPaint1.setBlendMode(SkBlendMode::kDstIn);
    canvas->saveLayer(&bounds1, &layerPaint1);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(2.0f, 1.0f, 18.0f, 21.0f), SkClipOp::kIntersect, true);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(2.0f, 1.0f, 18.0f, 21.0f), SkClipOp::kIntersect, false);
    canvas->concat(SkM44(1.0f, 0.0f, 0.0f, 0.0f,
                        0.0f, 1.0f, 0.0f, 0.0f,
                        0.0f, 0.0f, 1.0f, 0.0f,
                        0.0f, 0.0f, 0.0f, 1.0f));
    SkPathBuilder pathBuilder2;
    pathBuilder2.setFillType(SkPathFillType::kEvenOdd);
    pathBuilder2.moveTo(2.5f, 1.74286f);
    pathBuilder2.lineTo(17.5f, 1.74286f);
    pathBuilder2.lineTo(17.5f, 20.0762f);
    pathBuilder2.lineTo(2.5f, 20.0762f);
    pathBuilder2.lineTo(2.5f, 1.74286f);
    pathBuilder2.close();
    SkPath path2 = pathBuilder2.detach();
    SkPaint paint2;
    paint2.setAntiAlias(true);
    paint2.setColor(SkColorSetARGB(255, 255, 255, 255));
    canvas->drawPath(path2, paint2);
    canvas->restore();
    canvas->restore();
    canvas->restore();
    canvas->restore();
}

void draw_unit__ClipRect_1(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    canvas->drawOval(SkRect::MakeLTRB(10.0f, 0.0f, 260.0f, 120.0f), paint0);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 90.0f, 80.0f), SkClipOp::kIntersect, false);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 90.0f, 80.0f), SkClipOp::kIntersect, false);
    SkPaint paint1;
    canvas->drawOval(SkRect::MakeLTRB(40.0f, 0.0f, 160.0f, 120.0f), paint1);
    canvas->restore();
    SkPaint paint2;
    canvas->drawOval(SkRect::MakeLTRB(40.0f, 0.0f, 160.0f, 120.0f), paint2);
    canvas->restore();
}

void draw_unit__ClipRect_2(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint layerPaint0;
    layerPaint0.setColor(SkColorSetARGB(128, 0, 0, 0));
    canvas->saveLayer(nullptr, &layerPaint0);
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 90.0f, 80.0f), SkClipOp::kIntersect, false);
    SkPaint paint0;
    canvas->drawOval(SkRect::MakeLTRB(40.0f, 40.0f, 160.0f, 160.0f), paint0);
    canvas->restore();
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(90.0f, 90.0f, 110.0f, 130.0f), paint1);
}

void draw_unit__ClipRect_3(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(30.0f, 30.0f, 200.0f, 200.0f), SkClipOp::kIntersect, false);
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 35.0f, 35.0f), SkClipOp::kIntersect, false);
    SkPaint paint0;
    paint0.setAntiAlias(true);
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 10.0f, 500.0f, 500.0f), paint0);
    canvas->clipRect(SkRect::MakeLTRB(30.0f, 330.0f, 200.0f, 500.0f), SkClipOp::kDifference, false);
    canvas->clipRect(SkRect::MakeLTRB(300.0f, 300.0f, 500.0f, 500.0f), SkClipOp::kDifference, false);
    SkPaint paint1;
    paint1.setAntiAlias(true);
    paint1.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 310.0f, 500.0f, 400.0f), paint1);
    canvas->restore();
}

void draw_unit__Clip_over_SaveLayer(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->save();
    canvas->concat(SkM44(2.0f, 0.0f, 0.0f, 0.0f,
                        0.0f, 2.0f, 0.0f, 0.0f,
                        0.0f, 0.0f, 1.0f, 0.0f,
                        0.0f, 0.0f, 0.0f, 1.0f));
    SkPaint layerPaint0;
    canvas->saveLayer(nullptr, &layerPaint0);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    SkFont font;
    font.setSize(80.0f);
    font.setScaleX(0.3f);
    canvas->drawString("Hello", 20.0f, 100.0f, font, paint0);
    canvas->restore();
    canvas->restore();
}

void draw_unit__Draw(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(20.0f, 20.0f, 100.0f, 100.0f), paint0);
}

void draw_unit__Save(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->save();
    canvas->concat(SkM44(2.0f, 0.0f, 0.0f, 0.0f,
                        0.0f, 0.5f, 0.0f, 0.0f,
                        0.0f, 0.0f, 1.0f, 0.0f,
                        0.0f, 0.0f, 0.0f, 1.0f));
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 90.0f, 80.0f), SkClipOp::kIntersect, false);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(128, 0, 0, 255));
    canvas->drawOval(SkRect::MakeLTRB(40.0f, 40.0f, 160.0f, 160.0f), paint0);
    canvas->restore();
}

void draw_unit__SaveLayer_1(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(150.0f, 70.0f, 200.0f, 120.0f), paint0);
    canvas->saveLayer(nullptr, nullptr);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 70.0f, 220.0f, 120.0f), paint1);
    canvas->restore();
}

void draw_unit__SaveLayer_2(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 70.0f, 60.0f, 120.0f), paint0);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(150.0f, 70.0f, 200.0f, 120.0f), paint1);
    canvas->saveLayer(nullptr, nullptr);
    SkPaint paint2;
    paint2.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 70.0f, 80.0f, 120.0f), paint2);
    SkPaint paint3;
    paint3.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 70.0f, 220.0f, 120.0f), paint3);
    canvas->restore();
}

void draw_unit__SaveLayer_3(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 10.0f, 60.0f, 60.0f), paint0);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(150.0f, 10.0f, 200.0f, 60.0f), paint1);
    SkPaint paint2;
    paint2.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 10.0f, 80.0f, 60.0f), paint2);
    SkPaint paint3;
    paint3.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 10.0f, 220.0f, 60.0f), paint3);
    SkPaint paint4;
    paint4.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 70.0f, 60.0f, 120.0f), paint4);
    SkPaint paint5;
    paint5.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(150.0f, 70.0f, 200.0f, 120.0f), paint5);
    SkPaint layerPaint0;
    layerPaint0.setColor(SkColorSetARGB(77, 0, 0, 0));
    canvas->saveLayer(nullptr, &layerPaint0);
    SkPaint paint6;
    paint6.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 70.0f, 80.0f, 120.0f), paint6);
    SkPaint paint7;
    paint7.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 70.0f, 220.0f, 120.0f), paint7);
    canvas->restore();
    SkPaint layerPaint1;
    layerPaint1.setColor(SkColorSetARGB(77, 0, 0, 0));
    canvas->saveLayer(nullptr, &layerPaint1);
    SkPaint paint8;
    paint8.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 130.0f, 60.0f, 180.0f), paint8);
    SkPaint paint9;
    paint9.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(150.0f, 130.0f, 200.0f, 180.0f), paint9);
    SkPaint paint10;
    paint10.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 130.0f, 80.0f, 180.0f), paint10);
    SkPaint paint11;
    paint11.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 130.0f, 220.0f, 180.0f), paint11);
    canvas->restore();
}

void draw_unit__SaveLayer_4(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 2, 2, 2));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint0);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 2, 2, 2));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint1);
    SkPaint layerPaint0;
    layerPaint0.setBlendMode(SkBlendMode::kDstIn);
    canvas->saveLayer(nullptr, &layerPaint0);
    SkPaint paint2;
    paint2.setColor(SkColorSetARGB(255, 2, 2, 2));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint2);
    canvas->restore();
    SkPaint paint3;
    paint3.setColor(SkColorSetARGB(0, 2, 2, 2));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint3);
    SkPaint paint4;
    paint4.setColor(SkColorSetARGB(3, 2, 2, 2));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint4);
}

void draw_unit__SaveLayer_5(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 16, 32, 48));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 50.0f, 60.0f), paint0);
    SkPaint layerPaint0;
    layerPaint0.setColor(SkColorSetARGB(128, 128, 128, 128));
    canvas->saveLayer(nullptr, &layerPaint0);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 128, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 150.0f, 60.0f), paint1);
    canvas->restore();
}

void draw_unit__SaveLayer_over_Clip(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint layerPaint0;
    canvas->saveLayer(nullptr, &layerPaint0);
    canvas->concat(SkM44(2.0f, 0.0f, 0.0f, 0.0f,
                        0.0f, 2.0f, 0.0f, 0.0f,
                        0.0f, 0.0f, 1.0f, 0.0f,
                        0.0f, 0.0f, 0.0f, 1.0f));
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 0, 0));
    SkFont font;
    font.setSize(80.0f);
    font.setScaleX(0.3f);
    canvas->drawString("Hello", 20.0f, 100.0f, font, paint0);
    canvas->restore();
}

void draw_unit__nested_SaveLayer_1(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->saveLayer(nullptr, nullptr);
    canvas->saveLayer(nullptr, nullptr);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 70.0f, 60.0f, 120.0f), paint0);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(170.0f, 70.0f, 220.0f, 120.0f), paint1);
    canvas->restore();
    canvas->restore();
}

void draw_unit__nested_SaveLayer_2(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(128, 255, 0, 0));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 60.0f, 100.0f, 120.0f), paint0);
    canvas->saveLayer(nullptr, nullptr);
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(128, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(50.0f, 60.0f, 120.0f, 120.0f), paint1);
    canvas->saveLayer(nullptr, nullptr);
    SkPaint paint2;
    paint2.setColor(SkColorSetARGB(128, 0, 255, 0));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 30.0f, 90.0f, 100.0f), paint2);
    SkPaint paint3;
    paint3.setColor(SkColorSetARGB(128, 255, 255, 0));
    canvas->drawRect(SkRect::MakeLTRB(30.0f, 110.0f, 90.0f, 140.0f), paint3);
    canvas->restore();
    canvas->restore();
}

void draw_unit__noop_SaveLayer(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(10.0f, 70.0f, 60.0f, 120.0f), paint0);
    canvas->saveLayer(nullptr, nullptr);
    canvas->restore();
}

void draw_unit__noop_Save_1(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(90.0f, 90.0f, 110.0f, 130.0f), paint0);
    canvas->saveLayer(nullptr, nullptr);
    canvas->restore();
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(77, 0, 0, 255));
    canvas->drawRect(SkRect::MakeLTRB(110.0f, 130.0f, 190.0f, 190.0f), paint1);
}

void draw_unit__noop_Save_2(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 200.0f, 200.0f), SkClipOp::kIntersect, false);
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 100.0f, 100.0f), SkClipOp::kIntersect, false);
    canvas->restore();
}

void draw_unit__noop_Save_3(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->save();
    canvas->clipRect(SkRect::MakeLTRB(0.0f, 0.0f, 200.0f, 200.0f), SkClipOp::kIntersect, false);
    canvas->restore();
}

void draw_unit__state_over_SaveLayer(SkCanvas* canvas) {
    canvas->clear(SK_ColorTRANSPARENT);
    SkPaint paint0;
    paint0.setColor(SkColorSetARGB(255, 255, 255, 0));
    canvas->drawRect(SkRect::MakeLTRB(60.0f, 0.0f, 120.0f, 60.0f), paint0);
    canvas->save();
    canvas->concat(SkM44(2.0f, 0.0f, 0.0f, 0.0f,
                        0.0f, 2.0f, 0.0f, 0.0f,
                        0.0f, 0.0f, 1.0f, 0.0f,
                        0.0f, 0.0f, 0.0f, 1.0f));
    SkPaint paint1;
    paint1.setColor(SkColorSetARGB(255, 0, 255, 0));
    canvas->drawRect(SkRect::MakeLTRB(0.0f, 0.0f, 30.0f, 30.0f), paint1);
    SkPaint layerPaint0;
    canvas->saveLayer(nullptr, &layerPaint0);
    SkPaint paint2;
    paint2.setColor(SkColorSetARGB(255, 255, 0, 0));
    SkFont font;
    font.setSize(80.0f);
    font.setScaleX(0.3f);
    canvas->drawString("Hello", 20.0f, 100.0f, font, paint2);
    canvas->restore();
    canvas->restore();
}

struct CaseDef {
    const char* name;
    int width;
    int height;
    void (*draw_fn)(SkCanvas*);
};

constexpr int kDefaultW = 512;
constexpr int kDefaultH = 512;

const std::vector<CaseDef> kCases = {
        {"unit__ClipLayer", 1280, 64, draw_unit__ClipLayer},
        {"unit__ClipRect_1", kDefaultW, kDefaultH, draw_unit__ClipRect_1},
        {"unit__ClipRect_2", kDefaultW, kDefaultH, draw_unit__ClipRect_2},
        {"unit__ClipRect_3", kDefaultW, kDefaultH, draw_unit__ClipRect_3},
        {"unit__Clip_over_SaveLayer", kDefaultW, kDefaultH, draw_unit__Clip_over_SaveLayer},
        {"unit__Draw", kDefaultW, kDefaultH, draw_unit__Draw},
        {"unit__Save", kDefaultW, kDefaultH, draw_unit__Save},
        {"unit__SaveLayer_1", kDefaultW, kDefaultH, draw_unit__SaveLayer_1},
        {"unit__SaveLayer_2", kDefaultW, kDefaultH, draw_unit__SaveLayer_2},
        {"unit__SaveLayer_3", kDefaultW, kDefaultH, draw_unit__SaveLayer_3},
        {"unit__SaveLayer_4", kDefaultW, kDefaultH, draw_unit__SaveLayer_4},
        {"unit__SaveLayer_5", kDefaultW, kDefaultH, draw_unit__SaveLayer_5},
        {"unit__SaveLayer_over_Clip", kDefaultW, kDefaultH, draw_unit__SaveLayer_over_Clip},
        {"unit__nested_SaveLayer_1", kDefaultW, kDefaultH, draw_unit__nested_SaveLayer_1},
        {"unit__nested_SaveLayer_2", kDefaultW, kDefaultH, draw_unit__nested_SaveLayer_2},
        {"unit__noop_SaveLayer", kDefaultW, kDefaultH, draw_unit__noop_SaveLayer},
        {"unit__noop_Save_1", kDefaultW, kDefaultH, draw_unit__noop_Save_1},
        {"unit__noop_Save_2", kDefaultW, kDefaultH, draw_unit__noop_Save_2},
        {"unit__noop_Save_3", kDefaultW, kDefaultH, draw_unit__noop_Save_3},
        {"unit__state_over_SaveLayer", kDefaultW, kDefaultH, draw_unit__state_over_SaveLayer},
};

bool should_emit_case(const char* name) {
    return FLAGS_only.isEmpty() || FLAGS_only[0] == name;
}

bool emit_case(const CaseDef& def, const std::filesystem::path& out_dir) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(SkRect::MakeWH(def.width, def.height));
    def.draw_fn(canvas);

    sk_sp<SkPicture> picture = recorder.finishRecordingAsPicture();
    if (!picture) {
        SkDebugf("Failed to record case: %s\n", def.name);
        return false;
    }

    std::filesystem::path out_path = out_dir / (std::string(def.name) + ".skp");
    SkFILEWStream stream(out_path.c_str());
    if (!stream.isValid()) {
        SkDebugf("Failed to open output: %s\n", out_path.c_str());
        return false;
    }

    picture->serialize(&stream);
    SkDebugf("Wrote %s\n", out_path.c_str());
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    std::filesystem::path out_dir = FLAGS_output_dir[0];
    std::error_code ec;
    std::filesystem::create_directories(out_dir, ec);
    if (ec) {
        SkDebugf("Failed to create output dir '%s': %s\n", out_dir.c_str(), ec.message().c_str());
        return 1;
    }

    int attempted = 0;
    int written = 0;
    for (const auto& c : kCases) {
        if (!should_emit_case(c.name)) {
            continue;
        }
        attempted++;
        if (emit_case(c, out_dir)) {
            written++;
        }
    }

    if (attempted == 0) {
        SkDebugf("No matching cases. Use --only=<case_name> or omit --only.\n");
        return 2;
    }

    SkDebugf("Generated %d/%d SKPs in %s\n", written, attempted, out_dir.c_str());
    return written == attempted ? 0 : 3;
}
