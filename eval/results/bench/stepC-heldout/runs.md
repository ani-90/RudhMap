# Benchmark runs: stepC-heldout

One row per run. **Correct** = every required fact stated and no major false claim (Sonnet grader, majority of 3). **Tokens** = everything Claude Code counted for the run (new input + cache writes + cache reads + output). **New** = new content the model took in (input + cache writes). **Calls** = model calls (each re-sends the system prompt and conversation). **RM / Read / Grep / Glob** = tool calls by type (RM = RudhMap). **First** = tools used in the first model call. **After RM** = Read/Grep/Glob calls made after the first RudhMap answer. **$** = Claude Code's reported cost (cache reads billed at ~10%).

| Q | Setup | Model | Run | Correct | Facts | Tokens | New | Calls | RM | Read | Grep | Glob | First | After RM | $ | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rich-1 | Plain | haiku | 1 | yes | 4/5 | 94,726 | 20,191 | 6 | 0 | 12 | 3 | 0 | Grep+Grep | - | 0.0068 | 64s |
| rich-1 | Plain | haiku | 2 | yes | 5/5 | 153,768 | 22,313 | 9 | 0 | 17 | 5 | 0 | Grep+Grep | - | 0.0084 | 84s |
| rich-1 | Plain | haiku | 3 | yes | 5/5 | 75,014 | 13,860 | 6 | 0 | 11 | 3 | 0 | Grep+Grep | - | 0.0051 | 62s |
| rich-1 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 66,251 | 17,717 | 5 | 3 | 5 | 0 | 0 | rm:trace+rm:find_symbol | 5 | 0.0052 | 50s |
| rich-1 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 95,182 | 20,706 | 6 | 4 | 6 | 1 | 0 | rm:trace+rm:show | 7 | 0.0064 | 61s |
| rich-1 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 65,740 | 6,154 | 6 | 4 | 4 | 1 | 0 | rm:trace+rm:find_symbol | 5 | 0.0030 | 30s |
| rich-1 | RudhMap (nudged) | haiku | 1 | yes | 5/5 | 77,148 | 15,916 | 6 | 3 | 3 | 1 | 0 | rm:trace+rm:find_symbol | 4 | 0.0050 | 38s |
| rich-1 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 83,298 | 11,201 | 6 | 4 | 4 | 0 | 0 | rm:trace+rm:find_symbol | 4 | 0.0043 | 37s |
| rich-1 | RudhMap (nudged) | haiku | 3 | yes | 5/5 | 97,709 | 11,432 | 7 | 8 | 2 | 0 | 0 | rm:trace+rm:find_symbol | 2 | 0.0043 | 29s |
| rich-1 | RudhMap-only | haiku | 1 | no | 4/5 | 45,366 | 17,438 | 4 | 8 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0047 | 27s |
| rich-1 | RudhMap-only | haiku | 2 | no | 4/5 | 43,291 | 11,473 | 4 | 8 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0038 | 28s |
| rich-1 | RudhMap-only | haiku | 3 | yes | 5/5 | 68,393 | 14,844 | 5 | 7 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0046 | 28s |
| rich-1 | Plain | sonnet | 1 | yes | 5/5 | 35,603 | 7,999 | 4 | 0 | 3 | 2 | 0 | Grep | - | 0.0540 | 21s |
| rich-1 | Plain | sonnet | 2 | yes | 5/5 | 40,409 | 10,639 | 4 | 0 | 5 | 2 | 0 | Grep | - | 0.0659 | 22s |
| rich-1 | Plain | sonnet | 3 | yes | 5/5 | 36,352 | 8,831 | 4 | 0 | 4 | 2 | 0 | Grep | - | 0.0576 | 20s |
| rich-2 | Plain | haiku | 1 | yes | 4/4 | 64,764 | 9,588 | 5 | 0 | 5 | 2 | 0 | Grep+Grep | - | 0.0038 | 19s |
| rich-2 | Plain | haiku | 2 | yes | 4/4 | 30,801 | 6,221 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0024 | 13s |
| rich-2 | Plain | haiku | 3 | yes | 4/4 | 45,881 | 6,960 | 4 | 0 | 4 | 2 | 0 | Grep+Grep | - | 0.0028 | 16s |
| rich-2 | RudhMap (natural) | haiku | 1 | no | 3/4 | 60,409 | 11,497 | 4 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0037 | 23s |
| rich-2 | RudhMap (natural) | haiku | 2 | yes | 4/4 | 65,943 | 13,105 | 4 | 1 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0043 | 22s |
| rich-2 | RudhMap (natural) | haiku | 3 | yes | 4/4 | 72,735 | 10,141 | 5 | 1 | 4 | 2 | 0 | rm:find_symbol+Grep | 5 | 0.0037 | 23s |
| rich-2 | RudhMap (nudged) | haiku | 1 | yes | 4/4 | 53,654 | 7,088 | 5 | 5 | 2 | 1 | 0 | rm:find_symbol+rm:find_symbol | 3 | 0.0030 | 26s |
| rich-2 | RudhMap (nudged) | haiku | 2 | yes | 4/4 | 80,316 | 3,537 | 7 | 4 | 3 | 2 | 0 | rm:find_symbol+rm:find_symbol | 5 | 0.0027 | 28s |
| rich-2 | RudhMap (nudged) | haiku | 3 | no | 3/4 | 68,368 | 3,511 | 6 | 6 | 1 | 1 | 0 | rm:find_symbol+rm:find_symbol | 2 | 0.0026 | 28s |
| rich-2 | RudhMap-only | haiku | 1 | yes | 4/4 | 53,320 | 10,420 | 5 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0035 | 23s |
| rich-2 | RudhMap-only | haiku | 2 | no | 3/4 | 38,051 | 7,528 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0029 | 22s |
| rich-2 | RudhMap-only | haiku | 3 | yes | 4/4 | 38,368 | 7,578 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0028 | 23s |
| rich-2 | Plain | sonnet | 1 | yes | 4/4 | 30,631 | 4,661 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0365 | 20s |
| rich-2 | Plain | sonnet | 2 | yes | 4/4 | 31,136 | 4,847 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0377 | 21s |
| rich-2 | Plain | sonnet | 3 | yes | 4/4 | 22,510 | 4,249 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0317 | 15s |
| rich-3 | Plain | haiku | 1 | no | 2/5 | 48,973 | 5,698 | 5 | 0 | 5 | 3 | 0 | Grep+Grep | - | 0.0028 | 20s |
| rich-3 | Plain | haiku | 2 | yes | 4/5 | 40,391 | 5,533 | 4 | 0 | 3 | 3 | 0 | Grep+Grep | - | 0.0026 | 17s |
| rich-3 | Plain | haiku | 3 | no | 2/5 | 49,332 | 4,860 | 5 | 0 | 3 | 4 | 0 | Grep+Grep | - | 0.0025 | 17s |
| rich-3 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 48,236 | 7,967 | 4 | 2 | 3 | 1 | 0 | rm:show+rm:find_symbol | 4 | 0.0028 | 22s |
| rich-3 | RudhMap (natural) | haiku | 2 | no | 3/5 | 32,484 | 6,844 | 3 | 5 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0023 | 18s |
| rich-3 | RudhMap (natural) | haiku | 3 | no | 2/5 | 35,986 | 8,901 | 3 | 4 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0028 | 20s |
| rich-3 | RudhMap (nudged) | haiku | 1 | no | 3/5 | 40,414 | 10,595 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0031 | 21s |
| rich-3 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 40,884 | 9,764 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0032 | 20s |
| rich-3 | RudhMap (nudged) | haiku | 3 | yes | 5/5 | 40,737 | 2,375 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0017 | 18s |
| rich-3 | RudhMap-only | haiku | 1 | no | 3/5 | 39,578 | 8,242 | 4 | 6 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0027 | 23s |
| rich-3 | RudhMap-only | haiku | 2 | no | 3/5 | 25,200 | 5,396 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0020 | 18s |
| rich-3 | RudhMap-only | haiku | 3 | no | 3/5 | 37,185 | 6,412 | 4 | 7 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0023 | 18s |
| rich-3 | Plain | sonnet | 1 | yes | 4/5 | 24,400 | 4,862 | 3 | 0 | 4 | 2 | 0 | Grep+Grep | - | 0.0387 | 18s |
| rich-3 | Plain | sonnet | 2 | yes | 4/5 | 24,266 | 4,103 | 3 | 0 | 4 | 2 | 0 | Grep+Grep | - | 0.0350 | 17s |
| rich-3 | Plain | sonnet | 3 | yes | 4/5 | 23,948 | 3,784 | 3 | 0 | 4 | 2 | 0 | Grep+Grep | - | 0.0333 | 16s |
| rich-4 | Plain | haiku | 1 | yes | 3/4 | 26,655 | 4,614 | 3 | 0 | 5 | 2 | 0 | Grep+Grep | - | 0.0023 | 20s |
| rich-4 | Plain | haiku | 2 | yes | 3/4 | 25,036 | 2,919 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0016 | 17s |
| rich-4 | Plain | haiku | 3 | yes | 3/4 | 24,547 | 2,471 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0015 | 17s |
| rich-4 | RudhMap (natural) | haiku | 1 | no | 2/4 | 18,006 | 3,393 | 2 | 2 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0014 | 18s |
| rich-4 | RudhMap (natural) | haiku | 2 | no | 1/4 | 17,564 | 2,983 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0013 | 17s |
| rich-4 | RudhMap (natural) | haiku | 3 | no | 2/4 | 17,983 | 4 | 2 | 2 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0007 | 20s |
| rich-4 | RudhMap (nudged) | haiku | 1 | no | 1/4 | 17,926 | 2,983 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0014 | 22s |
| rich-4 | RudhMap (nudged) | haiku | 2 | no | 1/4 | 18,126 | 2,983 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0015 | 22s |
| rich-4 | RudhMap (nudged) | haiku | 3 | no | 2/4 | 17,674 | 4 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0007 | 18s |
| rich-4 | RudhMap-only | haiku | 1 | no | 1/4 | 13,106 | 2,983 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0012 | 16s |
| rich-4 | RudhMap-only | haiku | 2 | no | 1/4 | 13,009 | 2,983 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0012 | 14s |
| rich-4 | RudhMap-only | haiku | 3 | no | 2/4 | 22,656 | 3,112 | 3 | 3 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0015 | 18s |
| rich-4 | Plain | sonnet | 1 | yes | 3/4 | 21,221 | 2,921 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0260 | 16s |
| rich-4 | Plain | sonnet | 2 | yes | 3/4 | 20,986 | 2,081 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0223 | 16s |
| rich-4 | Plain | sonnet | 3 | yes | 3/4 | 20,978 | 2,038 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0224 | 15s |
| kna-h1 | Plain | haiku | 1 | no | 2/4 | 34,096 | 6,841 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0022 | 11s |
| kna-h1 | Plain | haiku | 2 | yes | 4/4 | 34,199 | 3,323 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0015 | 12s |
| kna-h1 | Plain | haiku | 3 | no | 3/4 | 34,179 | 351 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0009 | 13s |
| kna-h1 | RudhMap (natural) | haiku | 1 | yes | 3/4 | 46,586 | 6,984 | 5 | 3 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0024 | 20s |
| kna-h1 | RudhMap (natural) | haiku | 2 | no | 3/4 | 35,969 | 5,491 | 4 | 2 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0020 | 16s |
| kna-h1 | RudhMap (natural) | haiku | 3 | no | 3/4 | 35,369 | 909 | 4 | 2 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0011 | 20s |
| kna-h1 | RudhMap (nudged) | haiku | 1 | no | 3/4 | 36,517 | 6,904 | 4 | 4 | 1 | 0 | 0 | rm:find_symbol+rm:find_symbol | 1 | 0.0023 | 21s |
| kna-h1 | RudhMap (nudged) | haiku | 2 | yes | 4/4 | 47,126 | 2,872 | 5 | 4 | 1 | 0 | 0 | rm:find_symbol+rm:find_symbol | 1 | 0.0017 | 20s |
| kna-h1 | RudhMap (nudged) | haiku | 3 | no | 3/4 | 34,940 | 259 | 4 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 19s |
| kna-h1 | RudhMap-only | haiku | 1 | no | 2/4 | 35,152 | 6,859 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0024 | 25s |
| kna-h1 | RudhMap-only | haiku | 2 | no | 3/4 | 33,509 | 4,570 | 5 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0018 | 23s |
| kna-h1 | RudhMap-only | haiku | 3 | no | 3/4 | 34,968 | 1,454 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0013 | 22s |
| kna-h1 | Plain | sonnet | 1 | no | 2/4 | 27,962 | 4,618 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0344 | 18s |
| kna-h1 | Plain | sonnet | 2 | no | 2/4 | 27,987 | 605 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0197 | 19s |
| kna-h1 | Plain | sonnet | 3 | no | 2/4 | 27,844 | 1,850 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0236 | 17s |
| tpl-h1 | Plain | haiku | 1 | yes | 2/4 | 52,389 | 12,618 | 4 | 0 | 3 | 2 | 0 | Grep | - | 0.0036 | 19s |
| tpl-h1 | Plain | haiku | 2 | yes | 2/4 | 63,441 | 12,019 | 5 | 0 | 3 | 4 | 0 | Grep | - | 0.0037 | 24s |
| tpl-h1 | Plain | haiku | 3 | yes | 2/4 | 49,920 | 8,159 | 4 | 0 | 3 | 1 | 0 | Grep | - | 0.0026 | 16s |
| tpl-h1 | RudhMap (natural) | haiku | 1 | yes | 2/4 | 57,011 | 13,307 | 4 | 1 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0037 | 22s |
| tpl-h1 | RudhMap (natural) | haiku | 2 | yes | 2/4 | 40,480 | 7,585 | 4 | 0 | 3 | 2 | 0 | Grep | - | 0.0024 | 22s |
| tpl-h1 | RudhMap (natural) | haiku | 3 | yes | 2/4 | 57,037 | 9,994 | 4 | 1 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0031 | 20s |
| tpl-h1 | RudhMap (nudged) | haiku | 1 | yes | 3/4 | 49,373 | 7,264 | 5 | 7 | 1 | 1 | 0 | rm:find_symbol+rm:find_symbol | 2 | 0.0026 | 28s |
| tpl-h1 | RudhMap (nudged) | haiku | 2 | yes | 3/4 | 61,719 | 2,963 | 6 | 6 | 1 | 2 | 0 | rm:find_symbol+rm:find_symbol | 3 | 0.0020 | 34s |
| tpl-h1 | RudhMap (nudged) | haiku | 3 | yes | 2/4 | 56,309 | 9,677 | 4 | 4 | 0 | 2 | 0 | rm:find_symbol+Grep | 1 | 0.0030 | 27s |
| tpl-h1 | RudhMap-only | haiku | 1 | no | 2/4 | 39,751 | 8,670 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0029 | 42s |
| tpl-h1 | RudhMap-only | haiku | 2 | no | 3/4 | 40,266 | 3,177 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 40s |
| tpl-h1 | RudhMap-only | haiku | 3 | no | 2/4 | 40,718 | 3,513 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0019 | 37s |
| tpl-h1 | Plain | sonnet | 1 | yes | 2/4 | 33,482 | 6,458 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0430 | 22s |
| tpl-h1 | Plain | sonnet | 2 | no | 1/4 | 21,913 | 2,476 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0208 | 13s |
| tpl-h1 | Plain | sonnet | 3 | yes | 3/4 | 31,366 | 3,244 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0278 | 19s |
| tpl-h2 | Plain | haiku | 1 | yes | 5/5 | 76,850 | 15,755 | 5 | 0 | 8 | 2 | 1 | Grep+Glob | - | 0.0051 | 24s |
| tpl-h2 | Plain | haiku | 2 | yes | 5/5 | 51,935 | 7,337 | 5 | 0 | 4 | 3 | 0 | Grep | - | 0.0030 | 21s |
| tpl-h2 | Plain | haiku | 3 | yes | 5/5 | 49,639 | 6,177 | 5 | 0 | 5 | 5 | 0 | Grep | - | 0.0030 | 22s |
| tpl-h2 | RudhMap (natural) | haiku | 1 | no | 4/5 | 42,650 | 7,583 | 4 | 5 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0027 | 25s |
| tpl-h2 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 57,303 | 8,156 | 5 | 5 | 1 | 2 | 0 | rm:find_symbol+Grep | 2 | 0.0030 | 25s |
| tpl-h2 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 57,455 | 621 | 5 | 5 | 1 | 3 | 0 | rm:find_symbol+Grep | 3 | 0.0016 | 28s |
| tpl-h2 | RudhMap (nudged) | haiku | 1 | no | 4/5 | 64,785 | 10,558 | 5 | 10 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0036 | 22s |
| tpl-h2 | RudhMap (nudged) | haiku | 2 | no | 4/5 | 80,658 | 11,194 | 6 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0040 | 24s |
| tpl-h2 | RudhMap (nudged) | haiku | 3 | no | 3/5 | 82,067 | 7,135 | 6 | 11 | 1 | 0 | 0 | rm:find_symbol+rm:repo_map | 1 | 0.0032 | 23s |
| tpl-h2 | RudhMap-only | haiku | 1 | yes | 4/5 | 69,193 | 12,986 | 6 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0041 | 23s |
| tpl-h2 | RudhMap-only | haiku | 2 | yes | 5/5 | 74,064 | 9,366 | 6 | 13 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0035 | 26s |
| tpl-h2 | RudhMap-only | haiku | 3 | yes | 5/5 | 55,279 | 7,773 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0031 | 23s |
| tpl-h2 | Plain | sonnet | 1 | yes | 5/5 | 25,228 | 5,225 | 3 | 0 | 3 | 2 | 0 | Grep | - | 0.0377 | 15s |
| tpl-h2 | Plain | sonnet | 2 | yes | 4/5 | 25,161 | 4,421 | 3 | 0 | 3 | 2 | 0 | Grep | - | 0.0347 | 16s |
| tpl-h2 | Plain | sonnet | 3 | no | 3/5 | 24,291 | 3,955 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0302 | 15s |
| httpx-h1 | Plain | haiku | 1 | yes | 3/4 | 59,420 | 10,740 | 5 | 0 | 5 | 3 | 1 | Grep+Glob | - | 0.0040 | 20s |
| httpx-h1 | Plain | haiku | 2 | yes | 3/4 | 47,955 | 7,660 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0031 | 16s |
| httpx-h1 | Plain | haiku | 3 | yes | 3/4 | 58,640 | 7,284 | 5 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0032 | 19s |
| httpx-h1 | RudhMap (natural) | haiku | 1 | yes | 3/4 | 50,498 | 11,840 | 4 | 3 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0034 | 19s |
| httpx-h1 | RudhMap (natural) | haiku | 2 | yes | 3/4 | 52,964 | 9,827 | 4 | 3 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0034 | 21s |
| httpx-h1 | RudhMap (natural) | haiku | 3 | yes | 3/4 | 48,695 | 7,277 | 4 | 1 | 4 | 1 | 0 | rm:find_symbol+Grep | 4 | 0.0027 | 19s |
| httpx-h1 | RudhMap (nudged) | haiku | 1 | no | 2/4 | 32,102 | 9,215 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:show+rm:show | 0 | 0.0028 | 18s |
| httpx-h1 | RudhMap (nudged) | haiku | 2 | yes | 3/4 | 46,321 | 7,752 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0027 | 21s |
| httpx-h1 | RudhMap (nudged) | haiku | 3 | no | 2/4 | 46,650 | 7,375 | 4 | 6 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0028 | 20s |
| httpx-h1 | RudhMap-only | haiku | 1 | yes | 3/4 | 57,629 | 15,302 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0044 | 22s |
| httpx-h1 | RudhMap-only | haiku | 2 | yes | 3/4 | 36,557 | 7,059 | 4 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0024 | 19s |
| httpx-h1 | RudhMap-only | haiku | 3 | no | 2/4 | 24,514 | 5,122 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0020 | 16s |
| httpx-h1 | Plain | sonnet | 1 | yes | 4/4 | 34,399 | 6,860 | 4 | 0 | 3 | 3 | 0 | Grep+Grep | - | 0.0470 | 21s |
| httpx-h1 | Plain | sonnet | 2 | yes | 4/4 | 34,870 | 4,717 | 4 | 0 | 3 | 3 | 0 | Grep+Grep | - | 0.0386 | 23s |
| httpx-h1 | Plain | sonnet | 3 | no | 3/4 | 23,561 | 3,711 | 3 | 0 | 2 | 3 | 0 | Grep | - | 0.0320 | 17s |

## Summary per setup

Per question the median of its 3 runs is taken, then the median across questions. A question counts as correct when at least 2 of its 3 runs are correct.

| Setup | Model | Correct questions | Correct runs | Median tokens / question | Median model calls | Median new content | Runs using RudhMap | RudhMap first | Built-in calls after RudhMap (mean) | Total $ |
|---|---|---|---|---|---|---|---|---|---|---|
| Plain | haiku | 6/8 | 20/24 | 50,454 | 4.5 | 7,148 | - | - | - | 0.08 |
| RudhMap (natural) | haiku | 5/8 | 15/24 | 53,754 | 4 | 8,897 | 23/24 | 23/24 | 2.5 | 0.07 |
| RudhMap (nudged) | haiku | 4/8 | 12/24 | 51,315 | 4.5 | 7,508 | 24/24 | 24/24 | 1.2 | 0.07 |
| RudhMap-only | haiku | 3/8 | 8/24 | 37,776 | 4 | 6,736 | 24/24 | 24/24 | 0.0 | 0.06 |
| Plain | sonnet | 7/8 | 18/24 | 29,296 | 4 | 4,262 | - | - | - | 0.85 |

## Step C pass criteria (eval/THRESHOLDS.md), Haiku

| Criterion | Target | Result | Pass |
|---|---|---|---|
| 1. Quality: correct questions >= plain Haiku | >= 6 | 5 | no |
| 2. Cost: median tokens <= 0.7 x plain Haiku | <= 35,318 | 53,754 (107% of plain) | no |
| 3. No question plain gets right and RudhMap gets wrong in all 3 runs | none | rich-4 | no (RCA needed) |

## Tokens per question (median of 3 runs)

| Q | Plain haiku | RudhMap (natural) haiku | RudhMap (nudged) haiku | RudhMap-only haiku | Plain sonnet |
|---|---|---|---|---|---|
| rich-1 | 94,726 (3/3) | 66,251 (3/3) | 83,298 (3/3) | 45,366 (1/3) | 36,352 (3/3) |
| rich-2 | 45,881 (3/3) | 65,943 (2/3) | 68,368 (2/3) | 38,368 (2/3) | 30,631 (3/3) |
| rich-3 | 48,973 (1/3) | 35,986 (1/3) | 40,737 (2/3) | 37,185 (0/3) | 24,266 (3/3) |
| rich-4 | 25,036 (3/3) | 17,983 (0/3) | 17,926 (0/3) | 13,106 (0/3) | 20,986 (3/3) |
| kna-h1 | 34,179 (1/3) | 35,969 (1/3) | 36,517 (1/3) | 34,968 (0/3) | 27,962 (0/3) |
| tpl-h1 | 52,389 (3/3) | 57,011 (3/3) | 56,309 (3/3) | 40,266 (0/3) | 31,366 (2/3) |
| tpl-h2 | 51,935 (3/3) | 57,303 (2/3) | 80,658 (0/3) | 69,193 (3/3) | 25,161 (2/3) |
| httpx-h1 | 58,640 (3/3) | 50,498 (3/3) | 46,321 (1/3) | 36,557 (2/3) | 34,399 (2/3) |
