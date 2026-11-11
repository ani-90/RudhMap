# Benchmark runs: stepC-r2

One row per run. **Correct** = every required fact stated and no major false claim (Sonnet grader, majority of 3). **Tokens** = everything Claude Code counted for the run (new input + cache writes + cache reads + output). **New** = new content the model took in (input + cache writes). **Calls** = model calls (each re-sends the system prompt and conversation). **RM / Read / Grep / Glob** = tool calls by type (RM = RudhMap). **First** = tools used in the first model call. **After RM** = Read/Grep/Glob calls made after the first RudhMap answer. **$** = Claude Code's reported cost (cache reads billed at ~10%).

| Q | Setup | Model | Run | Correct | Facts | Tokens | New | Calls | RM | Read | Grep | Glob | First | After RM | $ | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kna-1 | Plain | haiku | 1 | no | 3/5 | 17,531 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | Plain | haiku | 2 | no | 3/5 | 17,585 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 10s |
| kna-1 | Plain | haiku | 3 | no | 3/5 | 17,648 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | RudhMap (natural) | haiku | 1 | no | 3/5 | 18,069 | 3,130 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0015 | 17s |
| kna-1 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 26,512 | 3,204 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0014 | 17s |
| kna-1 | RudhMap (natural) | haiku | 3 | no | 3/5 | 18,071 | 3,130 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0015 | 17s |
| kna-1 | RudhMap-only | haiku | 1 | no | 3/5 | 13,678 | 7,381 | 2 | 3 | 0 | 0 | 0 | rm:show+rm:trace+rm:trace | 0 | 0.0022 | 16s |
| kna-1 | RudhMap-only | haiku | 2 | no | 3/5 | 13,536 | 7,381 | 2 | 3 | 0 | 0 | 0 | rm:show+rm:trace+rm:trace | 0 | 0.0022 | 15s |
| kna-1 | RudhMap-only | haiku | 3 | no | 3/5 | 13,669 | 7,381 | 2 | 3 | 0 | 0 | 0 | rm:show+rm:trace+rm:trace | 0 | 0.0022 | 16s |
| kna-1 | Plain | sonnet | 1 | no | 3/5 | 21,200 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0338 | 10s |
| kna-1 | Plain | sonnet | 2 | no | 3/5 | 21,233 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0342 | 10s |
| kna-1 | Plain | sonnet | 3 | no | 3/5 | 21,190 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0337 | 9s |
| kna-2 | Plain | haiku | 1 | no | 4/6 | 55,689 | 13,831 | 4 | 0 | 5 | 3 | 1 | Glob+Grep | - | 0.0048 | 19s |
| kna-2 | Plain | haiku | 2 | no | 3/6 | 55,344 | 15,775 | 4 | 0 | 7 | 2 | 1 | Glob+Grep | - | 0.0052 | 20s |
| kna-2 | Plain | haiku | 3 | yes | 6/6 | 81,174 | 17,691 | 5 | 0 | 12 | 1 | 1 | Glob | - | 0.0059 | 21s |
| kna-2 | RudhMap (natural) | haiku | 1 | no | 5/6 | 83,242 | 16,702 | 5 | 1 | 7 | 2 | 0 | rm:repo_map+Grep | 8 | 0.0060 | 31s |
| kna-2 | RudhMap (natural) | haiku | 2 | no | 4/6 | 67,288 | 11,060 | 5 | 10 | 1 | 2 | 0 | rm:repo_map+Grep | 2 | 0.0038 | 23s |
| kna-2 | RudhMap (natural) | haiku | 3 | no | 4/6 | 52,824 | 10,345 | 4 | 2 | 2 | 2 | 0 | rm:repo_map+Grep | 3 | 0.0036 | 23s |
| kna-2 | RudhMap-only | haiku | 1 | yes | 5/6 | 45,082 | 13,727 | 4 | 12 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0042 | 21s |
| kna-2 | RudhMap-only | haiku | 2 | no | 4/6 | 59,436 | 13,955 | 5 | 11 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0045 | 22s |
| kna-2 | RudhMap-only | haiku | 3 | yes | 5/6 | 43,773 | 10,544 | 4 | 12 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0041 | 25s |
| kna-2 | Plain | sonnet | 1 | no | 4/6 | 40,731 | 7,934 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0519 | 15s |
| kna-2 | Plain | sonnet | 2 | yes | 5/6 | 41,396 | 8,310 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0529 | 15s |
| kna-2 | Plain | sonnet | 3 | no | 4/6 | 40,143 | 6,958 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0481 | 14s |
| kna-3 | Plain | haiku | 1 | yes | 2/3 | 60,811 | 8,712 | 5 | 0 | 4 | 3 | 1 | Grep+Glob | - | 0.0033 | 15s |
| kna-3 | Plain | haiku | 2 | yes | 3/3 | 35,519 | 3,685 | 4 | 0 | 3 | 2 | 1 | Grep+Glob | - | 0.0021 | 15s |
| kna-3 | Plain | haiku | 3 | yes | 3/3 | 46,192 | 7,288 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0028 | 14s |
| kna-3 | RudhMap (natural) | haiku | 1 | yes | 3/3 | 45,805 | 7,135 | 4 | 0 | 2 | 2 | 1 | Grep+Glob | - | 0.0026 | 21s |
| kna-3 | RudhMap (natural) | haiku | 2 | yes | 2/3 | 48,442 | 7,453 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0027 | 20s |
| kna-3 | RudhMap (natural) | haiku | 3 | yes | 2/3 | 50,652 | 8,096 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0029 | 20s |
| kna-3 | RudhMap-only | haiku | 1 | yes | 2/3 | 30,106 | 5,124 | 4 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0020 | 18s |
| kna-3 | RudhMap-only | haiku | 2 | yes | 2/3 | 38,465 | 5,436 | 5 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0020 | 18s |
| kna-3 | RudhMap-only | haiku | 3 | yes | 2/3 | 30,031 | 1,039 | 4 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0012 | 19s |
| kna-3 | Plain | sonnet | 1 | yes | 2/3 | 28,147 | 2,744 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0255 | 12s |
| kna-3 | Plain | sonnet | 2 | yes | 3/3 | 29,725 | 3,551 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0292 | 12s |
| kna-3 | Plain | sonnet | 3 | yes | 2/3 | 36,427 | 5,746 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0396 | 13s |
| kna-4 | Plain | haiku | 1 | yes | 2/3 | 28,086 | 5,286 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| kna-4 | Plain | haiku | 2 | yes | 2/3 | 28,362 | 4,902 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0020 | 11s |
| kna-4 | Plain | haiku | 3 | yes | 3/3 | 29,073 | 5,415 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0022 | 12s |
| kna-4 | RudhMap (natural) | haiku | 1 | yes | 2/3 | 34,964 | 4,102 | 4 | 3 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0018 | 18s |
| kna-4 | RudhMap (natural) | haiku | 2 | yes | 2/3 | 35,387 | 3,850 | 4 | 4 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0017 | 18s |
| kna-4 | RudhMap (natural) | haiku | 3 | yes | 2/3 | 28,063 | 3,326 | 3 | 2 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0016 | 17s |
| kna-4 | RudhMap-only | haiku | 1 | yes | 2/3 | 19,949 | 4,355 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0016 | 16s |
| kna-4 | RudhMap-only | haiku | 2 | yes | 2/3 | 19,593 | 4,271 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0015 | 15s |
| kna-4 | RudhMap-only | haiku | 3 | yes | 2/3 | 19,865 | 2,957 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0013 | 17s |
| kna-4 | Plain | sonnet | 1 | yes | 2/3 | 29,958 | 4,204 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0299 | 11s |
| kna-4 | Plain | sonnet | 2 | yes | 2/3 | 30,418 | 4,611 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0318 | 11s |
| kna-4 | Plain | sonnet | 3 | yes | 2/3 | 30,057 | 3,438 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0273 | 11s |
| kna-5 | Plain | haiku | 1 | yes | 4/5 | 36,314 | 6,031 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0023 | 12s |
| kna-5 | Plain | haiku | 2 | yes | 4/5 | 36,588 | 5,458 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0024 | 14s |
| kna-5 | Plain | haiku | 3 | yes | 4/5 | 36,653 | 5,131 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0022 | 13s |
| kna-5 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 37,253 | 4,429 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 16s |
| kna-5 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 37,175 | 4,426 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 16s |
| kna-5 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 37,249 | 519 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0010 | 18s |
| kna-5 | RudhMap-only | haiku | 1 | yes | 4/5 | 28,288 | 4,470 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 19s |
| kna-5 | RudhMap-only | haiku | 2 | yes | 4/5 | 28,313 | 4,470 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 20s |
| kna-5 | RudhMap-only | haiku | 3 | yes | 4/5 | 28,298 | 516 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 17s |
| kna-5 | Plain | sonnet | 1 | yes | 4/5 | 31,503 | 5,573 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0402 | 13s |
| kna-5 | Plain | sonnet | 2 | yes | 4/5 | 31,522 | 5,586 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0403 | 13s |
| kna-5 | Plain | sonnet | 3 | yes | 4/5 | 31,272 | 4,660 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0366 | 13s |
| tpl-1 | Plain | haiku | 1 | yes | 5/5 | 31,708 | 9,601 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0030 | 12s |
| tpl-1 | Plain | haiku | 2 | yes | 5/5 | 26,552 | 3,835 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0018 | 12s |
| tpl-1 | Plain | haiku | 3 | yes | 5/5 | 31,430 | 6,380 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0023 | 11s |
| tpl-1 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 29,205 | 7,444 | 3 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0024 | 18s |
| tpl-1 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 41,012 | 7,866 | 4 | 1 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0027 | 19s |
| tpl-1 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 29,308 | 4,345 | 3 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0018 | 17s |
| tpl-1 | RudhMap-only | haiku | 1 | yes | 5/5 | 21,619 | 7,240 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0023 | 17s |
| tpl-1 | RudhMap-only | haiku | 2 | yes | 5/5 | 21,436 | 2,211 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0013 | 18s |
| tpl-1 | RudhMap-only | haiku | 3 | yes | 5/5 | 21,446 | 6 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 19s |
| tpl-1 | Plain | sonnet | 1 | no | 4/5 | 21,006 | 4,881 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-1 | Plain | sonnet | 2 | yes | 5/5 | 21,672 | 5,422 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0372 | 12s |
| tpl-1 | Plain | sonnet | 3 | yes | 5/5 | 21,242 | 5,041 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0351 | 12s |
| tpl-2 | Plain | haiku | 1 | yes | 3/4 | 26,983 | 5,666 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0023 | 13s |
| tpl-2 | Plain | haiku | 2 | yes | 3/4 | 26,916 | 4,926 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0021 | 13s |
| tpl-2 | Plain | haiku | 3 | yes | 3/4 | 26,769 | 4,912 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0020 | 14s |
| tpl-2 | RudhMap (natural) | haiku | 1 | yes | 3/4 | 29,533 | 6,074 | 3 | 1 | 3 | 1 | 0 | Grep+rm:trace | 3 | 0.0023 | 20s |
| tpl-2 | RudhMap (natural) | haiku | 2 | yes | 3/4 | 29,486 | 6,072 | 3 | 1 | 3 | 1 | 0 | Grep+rm:trace | 3 | 0.0022 | 18s |
| tpl-2 | RudhMap (natural) | haiku | 3 | yes | 3/4 | 30,433 | 5,748 | 3 | 1 | 3 | 1 | 0 | Grep+rm:trace | 3 | 0.0024 | 20s |
| tpl-2 | RudhMap-only | haiku | 1 | yes | 3/4 | 38,594 | 9,824 | 4 | 12 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0033 | 24s |
| tpl-2 | RudhMap-only | haiku | 2 | yes | 3/4 | 39,248 | 10,114 | 4 | 12 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0035 | 24s |
| tpl-2 | RudhMap-only | haiku | 3 | yes | 3/4 | 54,066 | 10,137 | 5 | 13 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0038 | 24s |
| tpl-2 | Plain | sonnet | 1 | yes | 3/4 | 23,173 | 5,012 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-2 | Plain | sonnet | 2 | yes | 3/4 | 22,434 | 4,068 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0329 | 13s |
| tpl-2 | Plain | sonnet | 3 | yes | 3/4 | 30,202 | 3,833 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0324 | 14s |
| tpl-3 | Plain | haiku | 1 | yes | 5/5 | 81,964 | 14,477 | 5 | 0 | 4 | 4 | 1 | Grep+Glob | - | 0.0051 | 20s |
| tpl-3 | Plain | haiku | 2 | yes | 5/5 | 171,297 | 19,605 | 8 | 0 | 11 | 6 | 1 | Glob+Grep | - | 0.0079 | 32s |
| tpl-3 | Plain | haiku | 3 | yes | 5/5 | 92,925 | 19,611 | 5 | 0 | 10 | 3 | 1 | Glob+Grep | - | 0.0064 | 22s |
| tpl-3 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 92,582 | 14,854 | 6 | 7 | 2 | 4 | 0 | rm:find_symbol+Grep | 5 | 0.0052 | 27s |
| tpl-3 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 76,916 | 10,335 | 6 | 5 | 4 | 3 | 0 | rm:find_symbol+Grep | 6 | 0.0042 | 26s |
| tpl-3 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 87,182 | 18,277 | 5 | 2 | 11 | 2 | 0 | rm:repo_map+rm:find_symbol | 13 | 0.0064 | 30s |
| tpl-3 | RudhMap-only | haiku | 1 | yes | 5/5 | 57,322 | 12,611 | 5 | 13 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0041 | 24s |
| tpl-3 | RudhMap-only | haiku | 2 | no | 3/5 | 101,987 | 17,265 | 7 | 18 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0058 | 31s |
| tpl-3 | RudhMap-only | haiku | 3 | ? | 0/? | 124,366 | 11,218 | 8 | 20 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0052 | 36s |
| tpl-3 | Plain | sonnet | 1 | yes | 4/5 | 23,221 | 4,296 | 3 | 0 | 3 | 3 | 0 | Grep | - | 0.0353 | 13s |
| tpl-3 | Plain | sonnet | 2 | yes | 5/5 | 46,363 | 5,839 | 5 | 0 | 3 | 7 | 0 | Grep | - | 0.0529 | 19s |
| tpl-3 | Plain | sonnet | 3 | yes | 4/5 | 38,592 | 5,892 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0456 | 15s |
| tpl-4 | Plain | haiku | 1 | no | 3/5 | 45,603 | 8,162 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0029 | 14s |
| tpl-4 | Plain | haiku | 2 | no | 3/5 | 28,690 | 5,268 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0020 | 10s |
| tpl-4 | Plain | haiku | 3 | no | 3/5 | 26,150 | 4,168 | 3 | 0 | 4 | 1 | 0 | Grep | - | 0.0019 | 12s |
| tpl-4 | RudhMap (natural) | haiku | 1 | ? | 0/? | 34,242 | 8,035 | 3 | 1 | 4 | 1 | 0 | Grep+rm:repo_map | 4 | 0.0026 | 17s |
| tpl-4 | RudhMap (natural) | haiku | 2 | ? | 0/? | 31,637 | 5,614 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0022 | 17s |
| tpl-4 | RudhMap (natural) | haiku | 3 | ? | 0/? | 34,315 | 7,202 | 3 | 1 | 4 | 1 | 0 | Grep+rm:repo_map | 4 | 0.0025 | 18s |
| tpl-4 | RudhMap-only | haiku | 1 | ? | 0/? | 26,639 | 7,833 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0024 | 17s |
| tpl-4 | RudhMap-only | haiku | 2 | ? | 0/? | 26,916 | 3,448 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0017 | 17s |
| tpl-4 | RudhMap-only | haiku | 3 | no | 2/5 | 27,254 | 7,235 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0024 | 21s |
| tpl-4 | Plain | sonnet | 1 | no | 4/5 | 20,894 | 2,577 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0234 | 10s |
| tpl-4 | Plain | sonnet | 2 | no | 3/5 | 21,058 | 2,042 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0214 | 11s |
| tpl-4 | Plain | sonnet | 3 | no | 4/5 | 21,146 | 2,007 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0213 | 11s |
| tpl-5 | Plain | haiku | 1 | yes | 4/4 | 34,365 | 4,228 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0017 | 11s |
| tpl-5 | Plain | haiku | 2 | yes | 4/4 | 24,542 | 3,487 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0015 | 10s |
| tpl-5 | Plain | haiku | 3 | yes | 4/4 | 32,254 | 2,340 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0013 | 11s |
| tpl-5 | RudhMap (natural) | haiku | 1 | ? | 0/? | 37,207 | 4,324 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0018 | 26s |
| tpl-5 | RudhMap (natural) | haiku | 2 | ? | 0/? | 36,951 | 3,465 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0016 | 27s |
| tpl-5 | RudhMap (natural) | haiku | 3 | ? | 0/? | 37,294 | 3,600 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0017 | 19s |
| tpl-5 | RudhMap-only | haiku | 1 | ? | 0/? | 25,699 | 3,249 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0014 | 18s |
| tpl-5 | RudhMap-only | haiku | 2 | ? | 0/? | 25,701 | 1,541 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0011 | 20s |
| tpl-5 | RudhMap-only | haiku | 3 | ? | 0/? | 25,610 | 597 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 18s |
| tpl-5 | Plain | sonnet | 1 | yes | 4/4 | 20,133 | 2,649 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0207 | 9s |
| tpl-5 | Plain | sonnet | 2 | yes | 4/4 | 19,330 | 726 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0124 | 8s |
| tpl-5 | Plain | sonnet | 3 | yes | 4/4 | 20,168 | 1,953 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0183 | 9s |
| httpx-1 | Plain | haiku | 1 | yes | 5/5 | 26,033 | 7,520 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0024 | 11s |
| httpx-1 | Plain | haiku | 2 | yes | 5/5 | 26,905 | 4,453 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0020 | 12s |
| httpx-1 | Plain | haiku | 3 | yes | 5/5 | 26,270 | 4,299 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0020 | 12s |
| httpx-1 | RudhMap (natural) | haiku | 1 | no | 4/5 | 46,592 | 10,426 | 4 | 8 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol | 0 | 0.0034 | 23s |
| httpx-1 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 21,664 | 5,691 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0021 | 19s |
| httpx-1 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 21,544 | 4 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0010 | 17s |
| httpx-1 | RudhMap-only | haiku | 1 | yes | 5/5 | 37,407 | 11,405 | 4 | 9 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol | 0 | 0.0035 | 21s |
| httpx-1 | RudhMap-only | haiku | 2 | yes | 5/5 | 38,236 | 11,796 | 4 | 10 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol | 0 | 0.0036 | 22s |
| httpx-1 | RudhMap-only | haiku | 3 | yes | 5/5 | 38,961 | 5,945 | 4 | 10 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol | 0 | 0.0026 | 23s |
| httpx-1 | Plain | sonnet | 1 | yes | 5/5 | 22,637 | 6,151 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0398 | 12s |
| httpx-1 | Plain | sonnet | 2 | yes | 5/5 | 22,533 | 3,984 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0306 | 11s |
| httpx-1 | Plain | sonnet | 3 | yes | 5/5 | 22,562 | 3,659 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0291 | 11s |
| httpx-2 | Plain | haiku | 1 | yes | 5/5 | 16,231 | 2,578 | 2 | 0 | 0 | 2 | 0 | Grep+Grep | - | 0.0014 | 10s |
| httpx-2 | Plain | haiku | 2 | yes | 5/5 | 24,411 | 2,840 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0016 | 11s |
| httpx-2 | Plain | haiku | 3 | yes | 4/5 | 25,656 | 3,159 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0017 | 11s |
| httpx-2 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 35,428 | 3,573 | 4 | 2 | 1 | 1 | 0 | rm:find_symbol+rm:trace | 2 | 0.0018 | 22s |
| httpx-2 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 44,014 | 1,538 | 5 | 2 | 0 | 3 | 0 | rm:find_symbol+rm:trace | 3 | 0.0016 | 24s |
| httpx-2 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 26,336 | 1,683 | 3 | 2 | 0 | 1 | 0 | rm:find_symbol+rm:trace | 1 | 0.0014 | 22s |
| httpx-2 | RudhMap-only | haiku | 1 | yes | 4/5 | 19,695 | 3,123 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:show+rm:trace | 0 | 0.0013 | 18s |
| httpx-2 | RudhMap-only | haiku | 2 | yes | 3/5 | 11,890 | 1,183 | 2 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:show+rm:trace | 0 | 0.0008 | 16s |
| httpx-2 | RudhMap-only | haiku | 3 | yes | 4/5 | 12,707 | 4 | 2 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:show+rm:trace | 0 | 0.0008 | 16s |
| httpx-2 | Plain | sonnet | 1 | yes | 5/5 | 14,828 | 3,232 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0246 | 10s |
| httpx-2 | Plain | sonnet | 2 | yes | 5/5 | 21,165 | 1,712 | 3 | 0 | 0 | 2 | 0 | Grep | - | 0.0195 | 11s |
| httpx-2 | Plain | sonnet | 3 | yes | 5/5 | 13,639 | 1,527 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0160 | 8s |
| httpx-3 | Plain | haiku | 1 | yes | 4/5 | 62,789 | 9,533 | 5 | 0 | 6 | 3 | 1 | Grep+Glob | - | 0.0039 | 18s |
| httpx-3 | Plain | haiku | 2 | yes | 4/5 | 58,573 | 7,393 | 5 | 0 | 3 | 4 | 0 | Grep | - | 0.0032 | 17s |
| httpx-3 | Plain | haiku | 3 | yes | 4/5 | 44,462 | 6,707 | 4 | 0 | 2 | 4 | 0 | Grep | - | 0.0028 | 15s |
| httpx-3 | RudhMap (natural) | haiku | 1 | no | 3/5 | 48,738 | 7,785 | 4 | 1 | 2 | 3 | 0 | Grep+rm:find_symbol | 4 | 0.0030 | 21s |
| httpx-3 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 49,800 | 9,013 | 4 | 1 | 4 | 2 | 0 | Grep+rm:find_symbol | 5 | 0.0033 | 21s |
| httpx-3 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 41,192 | 6,212 | 4 | 6 | 0 | 1 | 0 | rm:find_symbol+rm:show | 1 | 0.0026 | 20s |
| httpx-3 | RudhMap-only | haiku | 1 | no | 4/5 | 33,759 | 8,084 | 4 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0027 | 19s |
| httpx-3 | RudhMap-only | haiku | 2 | no | 3/5 | 32,154 | 2,359 | 4 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0016 | 20s |
| httpx-3 | RudhMap-only | haiku | 3 | no | 4/5 | 46,931 | 9,384 | 5 | 10 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0033 | 21s |
| httpx-3 | Plain | sonnet | 1 | yes | 4/5 | 38,241 | 5,157 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0428 | 16s |
| httpx-3 | Plain | sonnet | 2 | yes | 4/5 | 39,566 | 4,844 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0413 | 16s |
| httpx-3 | Plain | sonnet | 3 | yes | 4/5 | 37,967 | 3,936 | 5 | 0 | 0 | 6 | 1 | Grep | - | 0.0383 | 16s |
| httpx-4 | Plain | haiku | 1 | yes | 4/5 | 34,209 | 7,691 | 3 | 0 | 2 | 1 | 0 | Grep+Read | - | 0.0026 | 11s |
| httpx-4 | Plain | haiku | 2 | yes | 4/5 | 28,767 | 5,920 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0024 | 13s |
| httpx-4 | Plain | haiku | 3 | yes | 5/5 | 28,127 | 5,326 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| httpx-4 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 31,448 | 6,797 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0024 | 19s |
| httpx-4 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 31,727 | 6,207 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0022 | 19s |
| httpx-4 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 30,126 | 5,311 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0021 | 20s |
| httpx-4 | RudhMap-only | haiku | 1 | yes | 5/5 | 26,046 | 6,213 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0024 | 22s |
| httpx-4 | RudhMap-only | haiku | 2 | yes | 5/5 | 35,825 | 6,788 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0024 | 19s |
| httpx-4 | RudhMap-only | haiku | 3 | yes | 5/5 | 45,794 | 2,333 | 5 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0017 | 20s |
| httpx-4 | Plain | sonnet | 1 | yes | 4/5 | 24,143 | 5,032 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0368 | 13s |
| httpx-4 | Plain | sonnet | 2 | yes | 5/5 | 25,897 | 5,843 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0425 | 15s |
| httpx-4 | Plain | sonnet | 3 | yes | 5/5 | 23,035 | 3,710 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0305 | 13s |
| httpx-5 | Plain | haiku | 1 | yes | 4/5 | 67,261 | 8,209 | 6 | 0 | 6 | 3 | 0 | Grep | - | 0.0035 | 18s |
| httpx-5 | Plain | haiku | 2 | yes | 4/5 | 68,436 | 10,893 | 5 | 0 | 6 | 2 | 0 | Grep | - | 0.0039 | 16s |
| httpx-5 | Plain | haiku | 3 | yes | 4/5 | 51,976 | 6,714 | 5 | 0 | 5 | 3 | 0 | Grep+Grep | - | 0.0030 | 17s |
| httpx-5 | RudhMap (natural) | haiku | 1 | yes | 3/5 | 63,516 | 6,488 | 6 | 5 | 3 | 1 | 0 | rm:find_symbol+rm:show | 4 | 0.0029 | 24s |
| httpx-5 | RudhMap (natural) | haiku | 2 | yes | 3/5 | 42,425 | 5,645 | 4 | 7 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0024 | 21s |
| httpx-5 | RudhMap (natural) | haiku | 3 | no | 2/5 | 60,688 | 7,869 | 5 | 5 | 2 | 2 | 0 | rm:find_symbol+Grep | 3 | 0.0031 | 23s |
| httpx-5 | RudhMap-only | haiku | 1 | yes | 3/5 | 39,486 | 6,417 | 5 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0025 | 25s |
| httpx-5 | RudhMap-only | haiku | 2 | no | 2/5 | 43,095 | 7,791 | 5 | 10 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0028 | 25s |
| httpx-5 | RudhMap-only | haiku | 3 | yes | 3/5 | 32,381 | 5,069 | 4 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0021 | 20s |
| httpx-5 | Plain | sonnet | 1 | yes | 4/5 | 23,795 | 4,884 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0366 | 14s |
| httpx-5 | Plain | sonnet | 2 | yes | 4/5 | 23,507 | 3,933 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0326 | 13s |
| httpx-5 | Plain | sonnet | 3 | yes | 4/5 | 22,104 | 3,247 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0272 | 12s |

## Summary per setup

Per question the median of its 3 runs is taken, then the median across questions. A question counts as correct when at least 2 of its 3 runs are correct.

| Setup | Model | Correct questions | Correct runs | Median tokens / question | Median model calls | Median new content | Runs using RudhMap | RudhMap first | Built-in calls after RudhMap (mean) | Total $ |
|---|---|---|---|---|---|---|---|---|---|---|
| Plain | haiku | 12/15 | 37/45 | 31,430 | 3 | 5,458 | - | - | - | 0.12 |
| RudhMap (natural) | haiku | 11/15 | 31/45 | 35,428 | 4 | 6,207 | 38/45 | 38/45 | 2.5 | 0.11 |
| RudhMap-only | haiku | 10/15 | 29/45 | 30,106 | 4 | 6,417 | 45/45 | 45/45 | 0.0 | 0.11 |
| Plain | sonnet | 12/15 | 36/45 | 23,507 | 3 | 4,204 | - | - | - | 1.50 |

## Step C pass criteria (eval/THRESHOLDS.md), Haiku

| Criterion | Target | Result | Pass |
|---|---|---|---|
| 1. Quality: correct questions >= plain Haiku | >= 12 | 11 | no |
| 2. Cost: median tokens <= 0.7 x plain Haiku | <= 22,001 | 35,428 (113% of plain) | no |
| 3. No question plain gets right and RudhMap gets wrong in all 3 runs | none | tpl-5 | no (RCA needed) |

## Tokens per question (median of 3 runs)

| Q | Plain haiku | RudhMap (natural) haiku | RudhMap-only haiku | Plain sonnet |
|---|---|---|---|---|
| kna-1 | 17,585 (0/3) | 18,071 (1/3) | 13,669 (0/3) | 21,200 (0/3) |
| kna-2 | 55,689 (1/3) | 67,288 (0/3) | 45,082 (2/3) | 40,731 (1/3) |
| kna-3 | 46,192 (3/3) | 48,442 (3/3) | 30,106 (3/3) | 29,725 (3/3) |
| kna-4 | 28,362 (3/3) | 34,964 (3/3) | 19,865 (3/3) | 30,057 (3/3) |
| kna-5 | 36,588 (3/3) | 37,249 (3/3) | 28,298 (3/3) | 31,503 (3/3) |
| tpl-1 | 31,430 (3/3) | 29,308 (3/3) | 21,446 (3/3) | 21,242 (2/3) |
| tpl-2 | 26,916 (3/3) | 29,533 (3/3) | 39,248 (3/3) | 23,173 (3/3) |
| tpl-3 | 92,925 (3/3) | 87,182 (3/3) | 101,987 (1/3) | 38,592 (3/3) |
| tpl-4 | 28,690 (0/3) | 34,242 (0/3) | 26,916 (0/3) | 21,058 (0/3) |
| tpl-5 | 32,254 (3/3) | 37,207 (0/3) | 25,699 (0/3) | 20,133 (3/3) |
| httpx-1 | 26,270 (3/3) | 21,664 (2/3) | 38,236 (3/3) | 22,562 (3/3) |
| httpx-2 | 24,411 (3/3) | 35,428 (3/3) | 12,707 (3/3) | 14,828 (3/3) |
| httpx-3 | 58,573 (3/3) | 48,738 (2/3) | 33,759 (0/3) | 38,241 (3/3) |
| httpx-4 | 28,767 (3/3) | 31,448 (3/3) | 35,825 (3/3) | 24,143 (3/3) |
| httpx-5 | 67,261 (3/3) | 60,688 (2/3) | 39,486 (2/3) | 23,507 (3/3) |
