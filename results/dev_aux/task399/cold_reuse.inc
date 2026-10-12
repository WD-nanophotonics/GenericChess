#if defined(DEV_AUX_COLD_REUSE) && defined(EVAL_MATERIAL) && MATERIAL_LEVEL == 1
    // DEV_AUX scoped single-Engine/fixed-option experiment; retain cold TT/history resets.
    static bool aux_previous_scoped_ready = false;
    const bool aux_scoped_ready = size_t(options["Threads"]) == 1
        && size_t(options["USI_Hash"]) == 16
        && std::string(options["NumaPolicy"]) == "auto"
        && std::string(options["BookFile"]) == "no_book";
    if (aux_previous_scoped_ready && aux_scoped_ready && threads.size() == 1) {
        threads.wait_for_search_finished();
        threads.clear(); // fills worker/shared histories, without invalidating shared references
    } else
        resize_threads();
    aux_previous_scoped_ready = aux_scoped_ready;
#else
    resize_threads();
#endif