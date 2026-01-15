#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <utility>
#include <vector>
#include "easteregg/easteregg.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkStream.h"
#include "include/core/SkString.h"
#include "include/private/base/SkDebug.h"
#include "src/base/SkTime.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/utils/SkJSONWriter.h"
#include "src/utils/SkOSPath.h"
#include "tools/flags/CommandLineFlags.h"

static DEFINE_string(
        skps, "", "A list of skps. Ensure the paths are correct. I do not do any error handling.");
static DEFINE_string(output, "", "Output folder for skps. Only for debugging");
static DEFINE_int(samples, 100, "#samples to run");

struct Stats {
    std::vector<double> samples;
    double minSample;
    double maxSample;
    double meanSample;
    double geomeanSample;

    Stats(std::vector<double> samples) : samples(std::move(samples)) {
        if (this->samples.empty()) {
            minSample = maxSample = meanSample = geomeanSample = 0.0;
            return;
        }

        maxSample = *std::max_element(this->samples.begin(), this->samples.end());
        minSample = *std::min_element(this->samples.begin(), this->samples.end());
        const double sum = std::accumulate(this->samples.begin(), this->samples.end(), 0.0);
        const double log_sum = std::accumulate(
                this->samples.begin(), this->samples.end(), 0.0, [](double acc, double value) {
                    return acc + std::log(value);
                });
        geomeanSample = std::exp(log_sum / this->samples.size());
        meanSample = sum / this->samples.size();
    }
};

struct SKPBench {
    SkString path;
    SkString name;
    sk_sp<SkPicture> picture;
    SkRect bounds;

    // THIS BREAKS IF YOU GIVE BAD PATHS. DO NOT GIVE BAD PATHS.
    SKPBench(SkString path) : path(std::move(path)) {
        name = SkOSPath::Basename(this->path.c_str());

        SkFILEStream stream(this->path.c_str());
        if (!stream.isValid()) {
            SkDebugf("Failed to open SKP %s\n", this->path.c_str());
            return;
        }

        picture = SkPicture::MakeFromStream(&stream);
        if (!picture) {
            SkDebugf("Failed to parse SKP %s\n", this->path.c_str());
            return;
        }

        bounds = picture->cullRect();
    }
};

class NanoJSONResultsWriter : public SkJSONWriter {
public:
    NanoJSONResultsWriter(SkWStream* stream, Mode mode) : SkJSONWriter(stream, mode) {}

    void beginBench(const char* name, int32_t x, int32_t y) {
        SkString id = SkStringPrintf("%s_%d_%d", name, x, y);
        this->beginObject(id.c_str());
    }

    void endBench() { this->endObject(); }

    void appendMetric(const char* name, double value) {
        // Don't record if NaN or Inf.
        if (std::isfinite(value)) {
            this->appendDoubleDigits(name, value, 16);
        }
    }
};

static double now_ns() { return static_cast<double>(SkTime::GetNSecs()); }

double estimate_timer_overhead_ns() {
    double overhead = 0.0;
    for (int i = 0; i < 100000; ++i) {
        const double start = now_ns();
        overhead += now_ns() - start;
    }
    return overhead / 100000;
}

void writeSkRecord(const SkRecord& records, const SkRect& bounds, std::string filename) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(bounds);
    if (!canvas) {
        SkDebugf("Error making canvas");
        return;
    }

    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);
    sk_sp<SkPicture> picture = recorder.finishRecordingAsPicture();

    SkFILEWStream stream(filename.c_str());
    picture->serialize(&stream);
    return;
}

double time(int loops,
            const sk_sp<SkPicture>& picture,
            bool write_to_file = false,
            int sample_index = 0) {
    SkRect bounds(picture->cullRect());
    std::vector<SkRecord> records(loops);

    // Make all the canvases
    for (auto& record : records) {
        SkRecordCanvas recorder(&record, bounds);
        picture->playback(&recorder);
    }

    RemoveOpaqueSaveLayers opt1;
    RemoveLoneLuma opt2;
    GradientDstInToMasks opt3;

    // Optimize
    auto start = SkTime::GetNSecs();
    for (int i = 0; i < loops; i++) {
        opt3.transform(&records[i]);
        opt2.transform(&records[i]);
        opt1.transform(&records[i]);
    }
    double duration = SkTime::GetNSecs() - start;

    if (write_to_file)
        writeSkRecord(records[0],
                      bounds,
                      std::string(FLAGS_output[0]) + "/" + std::to_string(sample_index) + ".skp");

    return duration;
}

int calculate_loops(const double overhead, const sk_sp<SkPicture>& picture) {
    double bench_plus_overhead = 0.0;
    int round = 0;

    while (bench_plus_overhead < overhead) {
        if (round++ == 3) {
            SkDebugf("bench + overhead < overhead \n");
            return -2;
        }
        bench_plus_overhead = time(1, picture);
    }

    // Later we'll just start and stop the timer once but loop N times.
    // We'll pick N to make timer overhead negligible:
    //
    //          overhead
    //  -------------------------  < FLAGS_overheadGoal
    //  overhead + N * Bench Time
    //
    // where bench_plus_overhead ~=~ overhead + Bench Time.
    //
    // Doing some math, we get:
    //
    //  (overhead / FLAGS_overheadGoal) - overhead
    //  ------------------------------------------  < N
    //       bench_plus_overhead - overhead)
    //
    // Luckily, this also works well in practice. :)

    const double numer = overhead / 0.0001 - overhead;
    const double denom = bench_plus_overhead - overhead;
    int loops = (int)ceil(numer / denom);
    if (loops < 1) {
        SkDebugf("Some error in loops\n");
        return 1;
    } else if (loops > 1000000) {
        return 1000000;
    } else {
        return loops;
    }
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    const double timerOverhead = estimate_timer_overhead_ns();
    SkDebugf("Timer overhead: %.2f ns\n", timerOverhead);

    // save skps into skpbench
    std::vector<SKPBench> benchmarks;
    std::vector<Stats> easteregg_stats;

    for (int i = 0; i < FLAGS_skps.size(); i++) {
        SKPBench bench{SkString(FLAGS_skps[i])};
        if (!bench.picture) {
            SkDebugf("Skipping invalid SKP %s\n", FLAGS_skps[i]);
            continue;
        }
        benchmarks.push_back(std::move(bench));
    }
    if (benchmarks.empty()) {
        SkDebugf("No valid SKPs provided.\n");
        return 1;
    }

    for (const auto& benchmark : benchmarks) {
        int easteregg_loops = calculate_loops(timerOverhead, benchmark.picture);
        if (easteregg_loops < 1) {
            SkDebugf("Failed to calibrate loops for %s (Easteregg)\n",
                     benchmark.name.c_str());
            continue;
        }
        std::vector<double> easteregg_samples;
        for (int i = 0; i < FLAGS_samples; i++) {
            double duration = time(easteregg_loops, benchmark.picture, true, i);
            easteregg_samples.push_back(duration / easteregg_loops);
        }
        easteregg_stats.push_back(Stats(easteregg_samples));
        std::cout << "Easteregg Geomean " << easteregg_stats.back().geomeanSample << "ns"
                  << std::endl;
    }
}

// const std::string outputPath = FLAGS_output[0];

// sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
// if (!picture) {
//     SkDebugf("Error loading skp from %s", FLAGS_input[0]);
//     return 1;
// }

// SkRect bounds(picture->cullRect());

// const double timerOverhead = estimate_timer_overhead_ns();
// SkDebugf("Timer overhead: %.2f ns\n", timerOverhead);

// std::function<void(SkRecord*)> recordOptimizer = [](SkRecord* record) {
//     SkRecordOptimize(record);
// };
// int loops = calculate_loops(timerOverhead, picture, recordOptimizer);

// std::vector<double> easter_egg;
// std::vector<double> skrecordopt;
// std::vector<double> samples;

// for (int i = 0; i < FLAGS_samples; i++) {
//     double duration = time(loops, picture, RemoveOpaqueSaveLayers(), true, i);
//     samples.push_back(duration / loops);
// }

// for (auto sample : samples) {
//     std::cout << sample << "ns" << std::endl;
// }

// SkFILEWStream opttime_json((std::string(FLAGS_output[0]) + "/" + "opttime.json").c_str());
// NanoJSONResultsWriter log(&opttime_json, SkJSONWriter::Mode::kPretty);
// return 0;
