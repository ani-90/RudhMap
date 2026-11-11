# Benchmark runs: stepC-r1

One row per run. **Correct** = every required fact stated and no major false claim (Sonnet grader, majority of 3). **Tokens** = everything Claude Code counted for the run (new input + cache writes + cache reads + output). **New** = new content the model took in (input + cache writes). **Calls** = model calls (each re-sends the system prompt and conversation). **RM / Read / Grep / Glob** = tool calls by type (RM = RudhMap). **First** = tools used in the first model call. **After RM** = Read/Grep/Glob calls made after the first RudhMap answer. **$** = Claude Code's reported cost (cache reads billed at ~10%).

| Q | Setup | Model | Run | Correct | Facts | Tokens | New | Calls | RM | Read | Grep | Glob | First | After RM | $ | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kna-1 | Plain | haiku | 1 | no | 3/5 | 17,531 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | Plain | haiku | 2 | no | 3/5 | 17,585 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 10s |
| kna-1 | Plain | haiku | 3 | no | 3/5 | 17,648 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | RudhMap (natural) | haiku | 1 | no | 3/5 | 20,066 | 4,609 | 2 | 1 | 1 | 0 | 0 | rm:show+Read | 0 | 0.0017 | 12s |
| kna-1 | RudhMap (natural) | haiku | 2 | no | 3/5 | 20,086 | 4,609 | 2 | 1 | 1 | 0 | 0 | rm:show+Read | 0 | 0.0017 | 12s |
| kna-1 | RudhMap (natural) | haiku | 3 | no | 3/5 | 20,102 | 4,609 | 2 | 1 | 1 | 0 | 0 | rm:show+Read | 0 | 0.0017 | 12s |
| kna-1 | RudhMap-only | haiku | 1 | no | 2/5 | 12,313 | 2,235 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0011 | 12s |
| kna-1 | RudhMap-only | haiku | 2 | no | 3/5 | 12,234 | 2,235 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0011 | 11s |
| kna-1 | RudhMap-only | haiku | 3 | no | 3/5 | 12,171 | 2,235 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0011 | 10s |
| kna-1 | Plain | sonnet | 1 | no | 3/5 | 21,200 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0338 | 10s |
| kna-1 | Plain | sonnet | 2 | no | 3/5 | 21,233 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0342 | 10s |
| kna-1 | Plain | sonnet | 3 | no | 3/5 | 21,190 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0337 | 9s |
| kna-2 | Plain | haiku | 1 | no | 4/6 | 55,689 | 13,831 | 4 | 0 | 5 | 3 | 1 | Glob+Grep | - | 0.0048 | 19s |
| kna-2 | Plain | haiku | 2 | no | 3/6 | 55,344 | 15,775 | 4 | 0 | 7 | 2 | 1 | Glob+Grep | - | 0.0052 | 20s |
| kna-2 | Plain | haiku | 3 | yes | 6/6 | 81,174 | 17,691 | 5 | 0 | 12 | 1 | 1 | Glob | - | 0.0059 | 21s |
| kna-2 | RudhMap (natural) | haiku | 1 | no | 4/6 | 67,216 | 10,705 | 5 | 11 | 0 | 1 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 1 | 0.0038 | 20s |
| kna-2 | RudhMap (natural) | haiku | 2 | no | 4/6 | 52,831 | 9,598 | 4 | 2 | 2 | 2 | 0 | rm:repo_map+Grep | 3 | 0.0034 | 18s |
| kna-2 | RudhMap (natural) | haiku | 3 | no | 4/6 | 68,175 | 10,383 | 5 | 12 | 0 | 1 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 1 | 0.0038 | 20s |
| kna-2 | RudhMap-only | haiku | 1 | no | 3/6 | 73,444 | 12,815 | 6 | 17 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0045 | 22s |
| kna-2 | RudhMap-only | haiku | 2 | no | 4/6 | 41,132 | 9,986 | 4 | 11 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0033 | 17s |
| kna-2 | RudhMap-only | haiku | 3 | no | 3/6 | 58,039 | 11,389 | 5 | 15 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0041 | 21s |
| kna-2 | Plain | sonnet | 1 | no | 4/6 | 40,731 | 7,934 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0519 | 15s |
| kna-2 | Plain | sonnet | 2 | yes | 5/6 | 41,396 | 8,310 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0529 | 15s |
| kna-2 | Plain | sonnet | 3 | no | 4/6 | 40,143 | 6,958 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0481 | 14s |
| kna-3 | Plain | haiku | 1 | yes | 2/3 | 60,811 | 8,712 | 5 | 0 | 4 | 3 | 1 | Grep+Glob | - | 0.0033 | 15s |
| kna-3 | Plain | haiku | 2 | yes | 3/3 | 35,519 | 3,685 | 4 | 0 | 3 | 2 | 1 | Grep+Glob | - | 0.0021 | 15s |
| kna-3 | Plain | haiku | 3 | yes | 3/3 | 46,192 | 7,288 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0028 | 14s |
| kna-3 | RudhMap (natural) | haiku | 1 | yes | 2/3 | 45,927 | 7,366 | 4 | 1 | 3 | 2 | 0 | Grep+rm:find_symbol | 4 | 0.0030 | 18s |
| kna-3 | RudhMap (natural) | haiku | 2 | yes | 3/3 | 46,802 | 6,735 | 4 | 1 | 3 | 2 | 0 | Grep+rm:find_symbol | 4 | 0.0027 | 15s |
| kna-3 | RudhMap (natural) | haiku | 3 | yes | 2/3 | 47,194 | 6,978 | 4 | 1 | 2 | 3 | 0 | Grep+rm:find_symbol | 4 | 0.0028 | 16s |
| kna-3 | RudhMap-only | haiku | 1 | yes | 1/3 | 39,002 | 5,190 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0021 | 16s |
| kna-3 | RudhMap-only | haiku | 2 | yes | 2/3 | 40,522 | 2,964 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0019 | 16s |
| kna-3 | RudhMap-only | haiku | 3 | yes | 1/3 | 49,555 | 2,428 | 6 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0018 | 18s |
| kna-3 | Plain | sonnet | 1 | yes | 2/3 | 28,147 | 2,744 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0255 | 12s |
| kna-3 | Plain | sonnet | 2 | yes | 3/3 | 29,725 | 3,551 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0292 | 12s |
| kna-3 | Plain | sonnet | 3 | yes | 2/3 | 36,427 | 5,746 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0396 | 13s |
| kna-4 | Plain | haiku | 1 | yes | 2/3 | 28,086 | 5,286 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| kna-4 | Plain | haiku | 2 | yes | 2/3 | 28,362 | 4,902 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0020 | 11s |
| kna-4 | Plain | haiku | 3 | yes | 3/3 | 29,073 | 5,415 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0022 | 12s |
| kna-4 | RudhMap (natural) | haiku | 1 | yes | 2/3 | 35,242 | 4,502 | 4 | 4 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0019 | 14s |
| kna-4 | RudhMap (natural) | haiku | 2 | yes | 2/3 | 35,212 | 3,723 | 4 | 4 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0017 | 14s |
| kna-4 | RudhMap (natural) | haiku | 3 | yes | 2/3 | 47,403 | 4,602 | 5 | 1 | 3 | 1 | 0 | Grep+Read | 1 | 0.0021 | 15s |
| kna-4 | RudhMap-only | haiku | 1 | yes | 2/3 | 19,540 | 4,191 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0015 | 12s |
| kna-4 | RudhMap-only | haiku | 2 | yes | 2/3 | 19,537 | 6 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0007 | 11s |
| kna-4 | RudhMap-only | haiku | 3 | yes | 2/3 | 19,555 | 6 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0007 | 12s |
| kna-4 | Plain | sonnet | 1 | yes | 2/3 | 29,958 | 4,204 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0299 | 11s |
| kna-4 | Plain | sonnet | 2 | yes | 2/3 | 30,418 | 4,611 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0318 | 11s |
| kna-4 | Plain | sonnet | 3 | yes | 2/3 | 30,057 | 3,438 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0273 | 11s |
| kna-5 | Plain | haiku | 1 | yes | 4/5 | 36,314 | 6,031 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0023 | 12s |
| kna-5 | Plain | haiku | 2 | yes | 4/5 | 36,588 | 5,458 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0024 | 14s |
| kna-5 | Plain | haiku | 3 | yes | 4/5 | 36,653 | 5,131 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0022 | 13s |
| kna-5 | RudhMap (natural) | haiku | 1 | no | 3/5 | 35,807 | 4,123 | 4 | 4 | 1 | 0 | 0 | rm:find_symbol+rm:find_symbol | 1 | 0.0018 | 15s |
| kna-5 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 57,826 | 2,446 | 6 | 6 | 1 | 0 | 0 | rm:find_symbol+rm:find_symbol | 1 | 0.0017 | 17s |
| kna-5 | RudhMap (natural) | haiku | 3 | no | 3/5 | 46,362 | 311 | 5 | 5 | 1 | 0 | 0 | rm:find_symbol+rm:find_symbol | 1 | 0.0011 | 15s |
| kna-5 | RudhMap-only | haiku | 1 | yes | 4/5 | 36,648 | 6,032 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0022 | 15s |
| kna-5 | RudhMap-only | haiku | 2 | yes | 4/5 | 46,070 | 3,835 | 6 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0020 | 17s |
| kna-5 | RudhMap-only | haiku | 3 | yes | 4/5 | 36,742 | 3,468 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0018 | 16s |
| kna-5 | Plain | sonnet | 1 | yes | 4/5 | 31,503 | 5,573 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0402 | 13s |
| kna-5 | Plain | sonnet | 2 | yes | 4/5 | 31,522 | 5,586 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0403 | 13s |
| kna-5 | Plain | sonnet | 3 | yes | 4/5 | 31,272 | 4,660 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0366 | 13s |
| tpl-1 | Plain | haiku | 1 | yes | 5/5 | 31,708 | 9,601 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0030 | 12s |
| tpl-1 | Plain | haiku | 2 | yes | 5/5 | 26,552 | 3,835 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0018 | 12s |
| tpl-1 | Plain | haiku | 3 | yes | 5/5 | 31,430 | 6,380 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0023 | 11s |
| tpl-1 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 41,326 | 8,052 | 4 | 1 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0027 | 14s |
| tpl-1 | RudhMap (natural) | haiku | 2 | no | 4/5 | 28,690 | 3,670 | 3 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0017 | 14s |
| tpl-1 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 29,720 | 4,391 | 3 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0020 | 14s |
| tpl-1 | RudhMap-only | haiku | 1 | no | 3/5 | 20,151 | 6,325 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0021 | 13s |
| tpl-1 | RudhMap-only | haiku | 2 | no | 3/5 | 19,916 | 6 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0008 | 12s |
| tpl-1 | RudhMap-only | haiku | 3 | no | 3/5 | 19,838 | 6 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0008 | 12s |
| tpl-1 | Plain | sonnet | 1 | no | 4/5 | 21,006 | 4,881 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-1 | Plain | sonnet | 2 | yes | 5/5 | 21,672 | 5,422 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0372 | 12s |
| tpl-1 | Plain | sonnet | 3 | yes | 5/5 | 21,242 | 5,041 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0351 | 12s |
| tpl-2 | Plain | haiku | 1 | yes | 3/4 | 26,983 | 5,666 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0023 | 13s |
| tpl-2 | Plain | haiku | 2 | yes | 3/4 | 26,916 | 4,926 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0021 | 13s |
| tpl-2 | Plain | haiku | 3 | yes | 3/4 | 26,769 | 4,912 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0020 | 14s |
| tpl-2 | RudhMap (natural) | haiku | 1 | yes | 3/4 | 30,088 | 6,772 | 3 | 1 | 3 | 1 | 0 | Grep+rm:trace | 3 | 0.0024 | 14s |
| tpl-2 | RudhMap (natural) | haiku | 2 | yes | 3/4 | 28,999 | 4,969 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0022 | 17s |
| tpl-2 | RudhMap (natural) | haiku | 3 | yes | 3/4 | 30,013 | 5,411 | 3 | 1 | 3 | 1 | 0 | Grep+rm:trace | 3 | 0.0024 | 17s |
| tpl-2 | RudhMap-only | haiku | 1 | yes | 3/4 | 50,472 | 9,279 | 5 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0036 | 22s |
| tpl-2 | RudhMap-only | haiku | 2 | yes | 3/4 | 36,879 | 7,424 | 4 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0029 | 18s |
| tpl-2 | RudhMap-only | haiku | 3 | yes | 3/4 | 37,227 | 8,468 | 4 | 12 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0029 | 16s |
| tpl-2 | Plain | sonnet | 1 | yes | 3/4 | 23,173 | 5,012 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-2 | Plain | sonnet | 2 | yes | 3/4 | 22,434 | 4,068 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0329 | 13s |
| tpl-2 | Plain | sonnet | 3 | yes | 3/4 | 30,202 | 3,833 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0324 | 14s |
| tpl-3 | Plain | haiku | 1 | yes | 5/5 | 81,964 | 14,477 | 5 | 0 | 4 | 4 | 1 | Grep+Glob | - | 0.0051 | 20s |
| tpl-3 | Plain | haiku | 2 | yes | 5/5 | 171,297 | 19,605 | 8 | 0 | 11 | 6 | 1 | Glob+Grep | - | 0.0079 | 32s |
| tpl-3 | Plain | haiku | 3 | yes | 5/5 | 92,925 | 19,611 | 5 | 0 | 10 | 3 | 1 | Glob+Grep | - | 0.0064 | 22s |
| tpl-3 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 67,469 | 11,388 | 5 | 1 | 6 | 5 | 0 | rm:find_symbol+Grep | 10 | 0.0045 | 23s |
| tpl-3 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 79,479 | 11,003 | 6 | 2 | 4 | 4 | 0 | rm:find_symbol+Grep | 7 | 0.0043 | 23s |
| tpl-3 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 58,456 | 9,693 | 5 | 5 | 1 | 5 | 0 | rm:find_symbol+Grep | 5 | 0.0040 | 22s |
| tpl-3 | RudhMap-only | haiku | 1 | no | 3/5 | 102,969 | 16,809 | 7 | 20 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0060 | 26s |
| tpl-3 | RudhMap-only | haiku | 2 | yes | 4/5 | 75,264 | 10,087 | 6 | 16 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0042 | 22s |
| tpl-3 | RudhMap-only | haiku | 3 | no | 3/5 | 72,179 | 8,317 | 6 | 14 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0035 | 20s |
| tpl-3 | Plain | sonnet | 1 | yes | 4/5 | 23,221 | 4,296 | 3 | 0 | 3 | 3 | 0 | Grep | - | 0.0353 | 13s |
| tpl-3 | Plain | sonnet | 2 | yes | 5/5 | 46,363 | 5,839 | 5 | 0 | 3 | 7 | 0 | Grep | - | 0.0529 | 19s |
| tpl-3 | Plain | sonnet | 3 | yes | 4/5 | 38,592 | 5,892 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0456 | 15s |
| tpl-4 | Plain | haiku | 1 | no | 3/5 | 45,603 | 8,162 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0029 | 14s |
| tpl-4 | Plain | haiku | 2 | no | 3/5 | 28,690 | 5,268 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0020 | 10s |
| tpl-4 | Plain | haiku | 3 | no | 3/5 | 26,150 | 4,168 | 3 | 0 | 4 | 1 | 0 | Grep | - | 0.0019 | 12s |
| tpl-4 | RudhMap (natural) | haiku | 1 | no | 3/5 | 33,685 | 7,806 | 3 | 1 | 4 | 1 | 0 | Grep+rm:repo_map | 4 | 0.0026 | 14s |
| tpl-4 | RudhMap (natural) | haiku | 2 | no | 3/5 | 29,423 | 5,285 | 3 | 1 | 3 | 1 | 0 | rm:find_symbol+Grep | 3 | 0.0021 | 16s |
| tpl-4 | RudhMap (natural) | haiku | 3 | no | 4/5 | 48,953 | 7,745 | 4 | 1 | 4 | 2 | 0 | Grep+rm:repo_map | 5 | 0.0028 | 15s |
| tpl-4 | RudhMap-only | haiku | 1 | no | 3/5 | 87,429 | 14,277 | 7 | 19 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0052 | 25s |
| tpl-4 | RudhMap-only | haiku | 2 | no | 4/5 | 70,848 | 12,857 | 6 | 16 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0047 | 22s |
| tpl-4 | RudhMap-only | haiku | 3 | no | 4/5 | 52,954 | 8,634 | 5 | 11 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0032 | 17s |
| tpl-4 | Plain | sonnet | 1 | no | 4/5 | 20,894 | 2,577 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0234 | 10s |
| tpl-4 | Plain | sonnet | 2 | no | 3/5 | 21,058 | 2,042 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0214 | 11s |
| tpl-4 | Plain | sonnet | 3 | no | 4/5 | 21,146 | 2,007 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0213 | 11s |
| tpl-5 | Plain | haiku | 1 | yes | 4/4 | 34,365 | 4,228 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0017 | 11s |
| tpl-5 | Plain | haiku | 2 | yes | 4/4 | 24,542 | 3,487 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0015 | 10s |
| tpl-5 | Plain | haiku | 3 | yes | 4/4 | 32,254 | 2,340 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0013 | 11s |
| tpl-5 | RudhMap (natural) | haiku | 1 | yes | 4/4 | 35,061 | 3,228 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0016 | 14s |
| tpl-5 | RudhMap (natural) | haiku | 2 | yes | 4/4 | 25,964 | 3,081 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0015 | 12s |
| tpl-5 | RudhMap (natural) | haiku | 3 | yes | 4/4 | 26,484 | 2,770 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0014 | 13s |
| tpl-5 | RudhMap-only | haiku | 1 | yes | 4/4 | 25,463 | 3,200 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0014 | 13s |
| tpl-5 | RudhMap-only | haiku | 2 | yes | 4/4 | 41,845 | 1,427 | 6 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0015 | 18s |
| tpl-5 | RudhMap-only | haiku | 3 | yes | 4/4 | 26,415 | 1,185 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0012 | 13s |
| tpl-5 | Plain | sonnet | 1 | yes | 4/4 | 20,133 | 2,649 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0207 | 9s |
| tpl-5 | Plain | sonnet | 2 | yes | 4/4 | 19,330 | 726 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0124 | 8s |
| tpl-5 | Plain | sonnet | 3 | yes | 4/4 | 20,168 | 1,953 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0183 | 9s |
| httpx-1 | Plain | haiku | 1 | yes | 5/5 | 26,033 | 7,520 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0024 | 11s |
| httpx-1 | Plain | haiku | 2 | yes | 5/5 | 26,905 | 4,453 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0020 | 12s |
| httpx-1 | Plain | haiku | 3 | yes | 5/5 | 26,270 | 4,299 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0020 | 12s |
| httpx-1 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 21,369 | 9,060 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0026 | 12s |
| httpx-1 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 31,540 | 5,736 | 3 | 3 | 2 | 0 | 0 | rm:show+rm:find_symbol+rm:find_symbol | 2 | 0.0022 | 13s |
| httpx-1 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 33,137 | 5,937 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show | 0 | 0.0022 | 12s |
| httpx-1 | RudhMap-only | haiku | 1 | yes | 5/5 | 26,284 | 10,482 | 3 | 8 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol | 0 | 0.0031 | 13s |
| httpx-1 | RudhMap-only | haiku | 2 | yes | 5/5 | 28,032 | 8,085 | 3 | 10 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol+rm:find_symbol+rm:find_symbol | 0 | 0.0026 | 13s |
| httpx-1 | RudhMap-only | haiku | 3 | no | 4/5 | 26,630 | 7,371 | 3 | 9 | 0 | 0 | 0 | rm:show+rm:trace+rm:find_symbol+rm:find_symbol | 0 | 0.0025 | 13s |
| httpx-1 | Plain | sonnet | 1 | yes | 5/5 | 22,637 | 6,151 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0398 | 12s |
| httpx-1 | Plain | sonnet | 2 | yes | 5/5 | 22,533 | 3,984 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0306 | 11s |
| httpx-1 | Plain | sonnet | 3 | yes | 5/5 | 22,562 | 3,659 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0291 | 11s |
| httpx-2 | Plain | haiku | 1 | yes | 5/5 | 16,231 | 2,578 | 2 | 0 | 0 | 2 | 0 | Grep+Grep | - | 0.0014 | 10s |
| httpx-2 | Plain | haiku | 2 | yes | 5/5 | 24,411 | 2,840 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0016 | 11s |
| httpx-2 | Plain | haiku | 3 | yes | 4/5 | 25,656 | 3,159 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0017 | 11s |
| httpx-2 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 35,268 | 3,377 | 4 | 2 | 1 | 1 | 0 | rm:find_symbol+rm:trace | 2 | 0.0019 | 16s |
| httpx-2 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 26,695 | 2,312 | 3 | 2 | 1 | 2 | 0 | rm:show+rm:trace+Grep | 2 | 0.0015 | 14s |
| httpx-2 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 27,189 | 2,898 | 3 | 2 | 1 | 2 | 0 | rm:find_symbol+rm:trace+Grep | 2 | 0.0017 | 14s |
| httpx-2 | RudhMap-only | haiku | 1 | yes | 3/5 | 18,224 | 2,448 | 3 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0012 | 12s |
| httpx-2 | RudhMap-only | haiku | 2 | yes | 3/5 | 11,554 | 4 | 2 | 2 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0006 | 11s |
| httpx-2 | RudhMap-only | haiku | 3 | yes | 3/5 | 18,347 | 707 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0010 | 14s |
| httpx-2 | Plain | sonnet | 1 | yes | 5/5 | 14,828 | 3,232 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0246 | 10s |
| httpx-2 | Plain | sonnet | 2 | yes | 5/5 | 21,165 | 1,712 | 3 | 0 | 0 | 2 | 0 | Grep | - | 0.0195 | 11s |
| httpx-2 | Plain | sonnet | 3 | yes | 5/5 | 13,639 | 1,527 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0160 | 8s |
| httpx-3 | Plain | haiku | 1 | yes | 4/5 | 62,789 | 9,533 | 5 | 0 | 6 | 3 | 1 | Grep+Glob | - | 0.0039 | 18s |
| httpx-3 | Plain | haiku | 2 | yes | 4/5 | 58,573 | 7,393 | 5 | 0 | 3 | 4 | 0 | Grep | - | 0.0032 | 17s |
| httpx-3 | Plain | haiku | 3 | yes | 4/5 | 44,462 | 6,707 | 4 | 0 | 2 | 4 | 0 | Grep | - | 0.0028 | 15s |
| httpx-3 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 57,820 | 8,107 | 5 | 3 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0032 | 17s |
| httpx-3 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 42,032 | 6,023 | 4 | 2 | 3 | 2 | 0 | rm:find_symbol+Grep | 4 | 0.0026 | 16s |
| httpx-3 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 69,459 | 9,308 | 5 | 1 | 3 | 3 | 0 | Grep+rm:show | 5 | 0.0038 | 19s |
| httpx-3 | RudhMap-only | haiku | 1 | no | 3/5 | 40,124 | 7,308 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0027 | 16s |
| httpx-3 | RudhMap-only | haiku | 2 | no | 4/5 | 30,756 | 6,122 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0022 | 15s |
| httpx-3 | RudhMap-only | haiku | 3 | no | 3/5 | 29,305 | 3,376 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 14s |
| httpx-3 | Plain | sonnet | 1 | yes | 4/5 | 38,241 | 5,157 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0428 | 16s |
| httpx-3 | Plain | sonnet | 2 | yes | 4/5 | 39,566 | 4,844 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0413 | 16s |
| httpx-3 | Plain | sonnet | 3 | yes | 4/5 | 37,967 | 3,936 | 5 | 0 | 0 | 6 | 1 | Grep | - | 0.0383 | 16s |
| httpx-4 | Plain | haiku | 1 | yes | 4/5 | 34,209 | 7,691 | 3 | 0 | 2 | 1 | 0 | Grep+Read | - | 0.0026 | 11s |
| httpx-4 | Plain | haiku | 2 | yes | 4/5 | 28,767 | 5,920 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0024 | 13s |
| httpx-4 | Plain | haiku | 3 | yes | 5/5 | 28,127 | 5,326 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| httpx-4 | RudhMap (natural) | haiku | 1 | no | 3/5 | 29,683 | 5,180 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0020 | 13s |
| httpx-4 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 31,354 | 6,048 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0022 | 14s |
| httpx-4 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 30,322 | 4,895 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0020 | 13s |
| httpx-4 | RudhMap-only | haiku | 1 | no | 3/5 | 28,839 | 5,137 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0020 | 14s |
| httpx-4 | RudhMap-only | haiku | 2 | yes | 4/5 | 21,598 | 3,358 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0016 | 13s |
| httpx-4 | RudhMap-only | haiku | 3 | no | 3/5 | 28,964 | 2,914 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0015 | 14s |
| httpx-4 | Plain | sonnet | 1 | yes | 4/5 | 24,143 | 5,032 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0368 | 13s |
| httpx-4 | Plain | sonnet | 2 | yes | 5/5 | 25,897 | 5,843 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0425 | 15s |
| httpx-4 | Plain | sonnet | 3 | yes | 5/5 | 23,035 | 3,710 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0305 | 13s |
| httpx-5 | Plain | haiku | 1 | yes | 4/5 | 67,261 | 8,209 | 6 | 0 | 6 | 3 | 0 | Grep | - | 0.0035 | 18s |
| httpx-5 | Plain | haiku | 2 | yes | 4/5 | 68,436 | 10,893 | 5 | 0 | 6 | 2 | 0 | Grep | - | 0.0039 | 16s |
| httpx-5 | Plain | haiku | 3 | yes | 4/5 | 51,976 | 6,714 | 5 | 0 | 5 | 3 | 0 | Grep+Grep | - | 0.0030 | 17s |
| httpx-5 | RudhMap (natural) | haiku | 1 | yes | 3/5 | 58,314 | 8,202 | 5 | 1 | 5 | 2 | 0 | rm:find_symbol+Grep | 6 | 0.0033 | 18s |
| httpx-5 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 53,601 | 5,846 | 5 | 1 | 4 | 2 | 0 | rm:find_symbol+Grep | 5 | 0.0027 | 20s |
| httpx-5 | RudhMap (natural) | haiku | 3 | yes | 3/5 | 40,134 | 4,932 | 4 | 6 | 2 | 0 | 0 | rm:find_symbol+rm:show | 2 | 0.0022 | 16s |
| httpx-5 | RudhMap-only | haiku | 1 | yes | 3/5 | 30,897 | 5,880 | 4 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0022 | 15s |
| httpx-5 | RudhMap-only | haiku | 2 | no | 2/5 | 42,218 | 5,174 | 5 | 10 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0024 | 19s |
| httpx-5 | RudhMap-only | haiku | 3 | yes | 3/5 | 20,838 | 2,684 | 3 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0014 | 13s |
| httpx-5 | Plain | sonnet | 1 | yes | 4/5 | 23,795 | 4,884 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0366 | 14s |
| httpx-5 | Plain | sonnet | 2 | yes | 4/5 | 23,507 | 3,933 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0326 | 13s |
| httpx-5 | Plain | sonnet | 3 | yes | 4/5 | 22,104 | 3,247 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0272 | 12s |

## Summary per setup

Per question the median of its 3 runs is taken, then the median across questions. A question counts as correct when at least 2 of its 3 runs are correct.

| Setup | Model | Correct questions | Correct runs | Median tokens / question | Median model calls | Median new content | Runs using RudhMap | RudhMap first | Built-in calls after RudhMap (mean) | Total $ |
|---|---|---|---|---|---|---|---|---|---|---|
| Plain | haiku | 12/15 | 37/45 | 31,430 | 3 | 5,458 | - | - | - | 0.12 |
| RudhMap (natural) | haiku | 11/15 | 32/45 | 33,685 | 3 | 5,411 | 41/45 | 40/45 | 2.7 | 0.11 |
| RudhMap-only | haiku | 8/15 | 24/45 | 30,756 | 4 | 3,835 | 45/45 | 45/45 | 0.0 | 0.10 |
| Plain | sonnet | 12/15 | 36/45 | 23,507 | 3 | 4,204 | - | - | - | 1.50 |

## Step C pass criteria (eval/THRESHOLDS.md), Haiku

| Criterion | Target | Result | Pass |
|---|---|---|---|
| 1. Quality: correct questions >= plain Haiku | >= 12 | 11 | no |
| 2. Cost: median tokens <= 0.7 x plain Haiku | <= 22,001 | 33,685 (107% of plain) | no |
| 3. No question plain gets right and RudhMap gets wrong in all 3 runs | none | none | yes |

## Tokens per question (median of 3 runs)

| Q | Plain haiku | RudhMap (natural) haiku | RudhMap-only haiku | Plain sonnet |
|---|---|---|---|---|
| kna-1 | 17,585 (0/3) | 20,086 (0/3) | 12,234 (0/3) | 21,200 (0/3) |
| kna-2 | 55,689 (1/3) | 67,216 (0/3) | 58,039 (0/3) | 40,731 (1/3) |
| kna-3 | 46,192 (3/3) | 46,802 (3/3) | 40,522 (3/3) | 29,725 (3/3) |
| kna-4 | 28,362 (3/3) | 35,242 (3/3) | 19,540 (3/3) | 30,057 (3/3) |
| kna-5 | 36,588 (3/3) | 46,362 (1/3) | 36,742 (3/3) | 31,503 (3/3) |
| tpl-1 | 31,430 (3/3) | 29,720 (2/3) | 19,916 (0/3) | 21,242 (2/3) |
| tpl-2 | 26,916 (3/3) | 30,013 (3/3) | 37,227 (3/3) | 23,173 (3/3) |
| tpl-3 | 92,925 (3/3) | 67,469 (3/3) | 75,264 (1/3) | 38,592 (3/3) |
| tpl-4 | 28,690 (0/3) | 33,685 (0/3) | 70,848 (0/3) | 21,058 (0/3) |
| tpl-5 | 32,254 (3/3) | 26,484 (3/3) | 26,415 (3/3) | 20,133 (3/3) |
| httpx-1 | 26,270 (3/3) | 31,540 (3/3) | 26,630 (2/3) | 22,562 (3/3) |
| httpx-2 | 24,411 (3/3) | 27,189 (3/3) | 18,224 (3/3) | 14,828 (3/3) |
| httpx-3 | 58,573 (3/3) | 57,820 (3/3) | 30,756 (0/3) | 38,241 (3/3) |
| httpx-4 | 28,767 (3/3) | 30,322 (2/3) | 28,839 (1/3) | 24,143 (3/3) |
| httpx-5 | 67,261 (3/3) | 53,601 (3/3) | 30,897 (2/3) | 23,507 (3/3) |
