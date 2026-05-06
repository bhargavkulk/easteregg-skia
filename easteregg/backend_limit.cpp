#include <cstdio>
#include <memory>
#include <string>

#include "include/gpu/ganesh/GrDirectContext.h"
#include "include/gpu/graphite/Context.h"
#include "tools/flags/CommandLineFlags.h"
#include "tools/ganesh/GrContextFactory.h"
#include "tools/graphite/ContextFactory.h"
#include "tools/graphite/TestOptions.h"
#include "tools/gpu/ContextType.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(backend, "gl", "Backend: gl, grmtl, or grvk");

static skgpu::ContextType BackendContextType(const std::string& backend) {
    if (backend == "gl") {
        return skgpu::ContextType::kGL;
    }
    if (backend == "grmtl") {
        return skgpu::ContextType::kMetal;
    }
    if (backend == "grvk") {
        return skgpu::ContextType::kVulkan;
    }
    return skgpu::ContextType::kMock;
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    const std::string backend = FLAGS_backend[0];

    if (backend == "gl") {
        auto factory = std::make_unique<sk_gpu_test::GrContextFactory>();
        auto contextInfo = factory->getContextInfo(BackendContextType(backend));
        if (!contextInfo.directContext()) {
            ERROR("Failed to create a %s context", backend.c_str());
            return 1;
        }

        printf("%d\n", contextInfo.directContext()->maxRenderTargetSize());
        return 0;
    }

    if (backend == "grmtl" || backend == "grvk") {
        auto factory = std::make_unique<skiatest::graphite::ContextFactory>(
                skiatest::graphite::TestOptions{});
        auto contextInfo = factory->getContextInfo(BackendContextType(backend));
        if (!contextInfo.fContext) {
            ERROR("Failed to create a %s context", backend.c_str());
            return 1;
        }

        printf("%d\n", contextInfo.fContext->maxTextureSize());
        return 0;
    }

    ERROR("Unsupported backend '%s' (expected gl, grmtl, or grvk)", backend.c_str());
    return 1;
}
