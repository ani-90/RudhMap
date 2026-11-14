# Benchmark runs: stepC-r3

One row per run. **Correct** = every required fact stated and no major false claim (Sonnet grader, majority of 3). **Tokens** = everything Claude Code counted for the run (new input + cache writes + cache reads + output). **New** = new content the model took in (input + cache writes). **Calls** = model calls (each re-sends the system prompt and conversation). **RM / Read / Grep / Glob** = tool calls by type (RM = RudhMap). **First** = tools used in the first model call. **After RM** = Read/Grep/Glob calls made after the first RudhMap answer. **$** = Claude Code's reported cost (cache reads billed at ~10%).

| Q | Setup | Model | Run | Correct | Facts | Tokens | New | Calls | RM | Read | Grep | Glob | First | After RM | $ | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kna-1 | Plain | haiku | 1 | no | 3/5 | 17,531 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | Plain | haiku | 2 | no | 3/5 | 17,585 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 10s |
| kna-1 | Plain | haiku | 3 | no | 3/5 | 17,648 | 4,120 | 2 | 0 | 1 | 1 | 0 | Grep+Read | - | 0.0016 | 9s |
| kna-1 | RudhMap (natural) | haiku | 1 | no | 3/5 | 17,151 | 829 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0009 | 11s |
| kna-1 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 26,675 | 3,206 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0014 | 12s |
| kna-1 | RudhMap (natural) | haiku | 3 | no | 3/5 | 26,731 | 3,250 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0015 | 12s |
| kna-1 | RudhMap (nudged) | haiku | 1 | yes | 4/5 | 26,797 | 825 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0009 | 15s |
| kna-1 | RudhMap (nudged) | haiku | 2 | no | 3/5 | 17,236 | 4 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0007 | 15s |
| kna-1 | RudhMap (nudged) | haiku | 3 | yes | 4/5 | 26,932 | 846 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0010 | 15s |
| kna-1 | RudhMap-only | haiku | 1 | yes | 4/5 | 19,948 | 7,359 | 3 | 2 | 0 | 0 | 0 | rm:show | 0 | 0.0022 | 12s |
| kna-1 | RudhMap-only | haiku | 2 | no | 3/5 | 12,580 | 6,512 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0019 | 11s |
| kna-1 | RudhMap-only | haiku | 3 | no | 3/5 | 12,600 | 6,512 | 2 | 1 | 0 | 0 | 0 | rm:show | 0 | 0.0019 | 10s |
| kna-1 | Plain | sonnet | 1 | no | 3/5 | 21,200 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0338 | 10s |
| kna-1 | Plain | sonnet | 2 | no | 3/5 | 21,233 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0342 | 10s |
| kna-1 | Plain | sonnet | 3 | no | 3/5 | 21,190 | 5,650 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0337 | 9s |
| kna-2 | Plain | haiku | 1 | no | 4/6 | 55,689 | 13,831 | 4 | 0 | 5 | 3 | 1 | Glob+Grep | - | 0.0048 | 19s |
| kna-2 | Plain | haiku | 2 | no | 3/6 | 55,344 | 15,775 | 4 | 0 | 7 | 2 | 1 | Glob+Grep | - | 0.0052 | 20s |
| kna-2 | Plain | haiku | 3 | yes | 6/6 | 81,174 | 17,691 | 5 | 0 | 12 | 1 | 1 | Glob | - | 0.0059 | 21s |
| kna-2 | RudhMap (natural) | haiku | 1 | yes | 5/6 | 57,170 | 13,998 | 4 | 8 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0046 | 19s |
| kna-2 | RudhMap (natural) | haiku | 2 | no | 4/6 | 60,234 | 13,936 | 4 | 2 | 3 | 3 | 0 | rm:repo_map+Grep | 5 | 0.0048 | 21s |
| kna-2 | RudhMap (natural) | haiku | 3 | yes | 5/6 | 52,602 | 11,328 | 4 | 9 | 1 | 1 | 1 | rm:repo_map+Glob | 2 | 0.0039 | 17s |
| kna-2 | RudhMap (nudged) | haiku | 1 | yes | 5/6 | 35,931 | 10,467 | 3 | 5 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0036 | 17s |
| kna-2 | RudhMap (nudged) | haiku | 2 | yes | 6/6 | 58,932 | 13,640 | 4 | 7 | 1 | 0 | 0 | rm:repo_map+rm:find_symbol | 1 | 0.0045 | 18s |
| kna-2 | RudhMap (nudged) | haiku | 3 | yes | 5/6 | 51,186 | 9,886 | 4 | 5 | 1 | 0 | 0 | rm:repo_map+rm:find_symbol | 1 | 0.0034 | 16s |
| kna-2 | RudhMap-only | haiku | 1 | yes | 5/6 | 63,811 | 14,048 | 5 | 8 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0044 | 17s |
| kna-2 | RudhMap-only | haiku | 2 | yes | 5/6 | 28,466 | 8,047 | 3 | 6 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0028 | 15s |
| kna-2 | RudhMap-only | haiku | 3 | no | 4/6 | 44,051 | 10,656 | 4 | 12 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol+rm:find_symbol | 0 | 0.0034 | 14s |
| kna-2 | Plain | sonnet | 1 | no | 4/6 | 40,731 | 7,934 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0519 | 15s |
| kna-2 | Plain | sonnet | 2 | yes | 5/6 | 41,396 | 8,310 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0529 | 15s |
| kna-2 | Plain | sonnet | 3 | no | 4/6 | 40,143 | 6,958 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0481 | 14s |
| kna-3 | Plain | haiku | 1 | yes | 2/3 | 60,811 | 8,712 | 5 | 0 | 4 | 3 | 1 | Grep+Glob | - | 0.0033 | 15s |
| kna-3 | Plain | haiku | 2 | yes | 3/3 | 35,519 | 3,685 | 4 | 0 | 3 | 2 | 1 | Grep+Glob | - | 0.0021 | 15s |
| kna-3 | Plain | haiku | 3 | yes | 3/3 | 46,192 | 7,288 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0028 | 14s |
| kna-3 | RudhMap (natural) | haiku | 1 | yes | 3/3 | 63,116 | 8,298 | 5 | 1 | 2 | 4 | 0 | rm:find_symbol+Grep | 5 | 0.0032 | 16s |
| kna-3 | RudhMap (natural) | haiku | 2 | yes | 3/3 | 59,858 | 6,396 | 5 | 1 | 2 | 3 | 0 | rm:find_symbol+Grep | 4 | 0.0026 | 15s |
| kna-3 | RudhMap (natural) | haiku | 3 | yes | 3/3 | 54,841 | 5,321 | 5 | 1 | 2 | 3 | 0 | rm:find_symbol+Grep | 4 | 0.0023 | 15s |
| kna-3 | RudhMap (nudged) | haiku | 1 | yes | 2/3 | 41,831 | 6,036 | 4 | 4 | 0 | 1 | 0 | rm:find_symbol+rm:repo_map | 1 | 0.0021 | 12s |
| kna-3 | RudhMap (nudged) | haiku | 2 | yes | 2/3 | 41,667 | 4,651 | 4 | 5 | 0 | 1 | 0 | rm:find_symbol+rm:repo_map | 1 | 0.0019 | 13s |
| kna-3 | RudhMap (nudged) | haiku | 3 | yes | 2/3 | 41,216 | 4,517 | 4 | 3 | 0 | 1 | 0 | rm:find_symbol+rm:repo_map | 1 | 0.0018 | 13s |
| kna-3 | RudhMap-only | haiku | 1 | yes | 2/3 | 46,148 | 7,739 | 5 | 8 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0026 | 14s |
| kna-3 | RudhMap-only | haiku | 2 | yes | 2/3 | 33,655 | 5,153 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0019 | 12s |
| kna-3 | RudhMap-only | haiku | 3 | yes | 2/3 | 34,057 | 5,226 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol+rm:repo_map | 0 | 0.0021 | 14s |
| kna-3 | Plain | sonnet | 1 | yes | 2/3 | 28,147 | 2,744 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0255 | 12s |
| kna-3 | Plain | sonnet | 2 | yes | 3/3 | 29,725 | 3,551 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0292 | 12s |
| kna-3 | Plain | sonnet | 3 | yes | 2/3 | 36,427 | 5,746 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0396 | 13s |
| kna-4 | Plain | haiku | 1 | yes | 2/3 | 28,086 | 5,286 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| kna-4 | Plain | haiku | 2 | yes | 2/3 | 28,362 | 4,902 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0020 | 11s |
| kna-4 | Plain | haiku | 3 | yes | 3/3 | 29,073 | 5,415 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0022 | 12s |
| kna-4 | RudhMap (natural) | haiku | 1 | yes | 2/3 | 48,762 | 5,886 | 5 | 2 | 2 | 2 | 0 | Grep | 3 | 0.0023 | 15s |
| kna-4 | RudhMap (natural) | haiku | 2 | yes | 3/3 | 38,652 | 5,582 | 4 | 0 | 3 | 2 | 0 | Grep | - | 0.0022 | 15s |
| kna-4 | RudhMap (natural) | haiku | 3 | yes | 2/3 | 28,270 | 3,516 | 3 | 2 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0015 | 12s |
| kna-4 | RudhMap (nudged) | haiku | 1 | yes | 2/3 | 36,494 | 4,771 | 4 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0018 | 12s |
| kna-4 | RudhMap (nudged) | haiku | 2 | yes | 2/3 | 38,820 | 4,022 | 4 | 4 | 0 | 1 | 0 | rm:show+rm:find_symbol | 1 | 0.0017 | 13s |
| kna-4 | RudhMap (nudged) | haiku | 3 | yes | 2/3 | 38,898 | 3,140 | 4 | 4 | 0 | 1 | 0 | rm:show+rm:find_symbol | 1 | 0.0016 | 13s |
| kna-4 | RudhMap-only | haiku | 1 | yes | 2/3 | 26,341 | 4,588 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0017 | 13s |
| kna-4 | RudhMap-only | haiku | 2 | yes | 2/3 | 28,219 | 4,408 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0017 | 13s |
| kna-4 | RudhMap-only | haiku | 3 | yes | 2/3 | 26,212 | 3,755 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0015 | 12s |
| kna-4 | Plain | sonnet | 1 | yes | 2/3 | 29,958 | 4,204 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0299 | 11s |
| kna-4 | Plain | sonnet | 2 | yes | 2/3 | 30,418 | 4,611 | 4 | 0 | 2 | 2 | 0 | Grep | - | 0.0318 | 11s |
| kna-4 | Plain | sonnet | 3 | yes | 2/3 | 30,057 | 3,438 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0273 | 11s |
| kna-5 | Plain | haiku | 1 | yes | 4/5 | 36,314 | 6,031 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0023 | 12s |
| kna-5 | Plain | haiku | 2 | yes | 4/5 | 36,588 | 5,458 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0024 | 14s |
| kna-5 | Plain | haiku | 3 | yes | 4/5 | 36,653 | 5,131 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0022 | 13s |
| kna-5 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 38,448 | 5,582 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0021 | 12s |
| kna-5 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 39,125 | 5,116 | 4 | 4 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0020 | 13s |
| kna-5 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 38,406 | 8 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0010 | 12s |
| kna-5 | RudhMap (nudged) | haiku | 1 | yes | 4/5 | 40,298 | 6,112 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0023 | 14s |
| kna-5 | RudhMap (nudged) | haiku | 2 | yes | 4/5 | 30,854 | 6,660 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0022 | 11s |
| kna-5 | RudhMap (nudged) | haiku | 3 | yes | 4/5 | 40,004 | 5,232 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0021 | 13s |
| kna-5 | RudhMap-only | haiku | 1 | yes | 4/5 | 29,903 | 5,748 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0020 | 13s |
| kna-5 | RudhMap-only | haiku | 2 | yes | 4/5 | 29,855 | 2,002 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0013 | 14s |
| kna-5 | RudhMap-only | haiku | 3 | yes | 4/5 | 29,871 | 8 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 13s |
| kna-5 | Plain | sonnet | 1 | yes | 4/5 | 31,503 | 5,573 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0402 | 13s |
| kna-5 | Plain | sonnet | 2 | yes | 4/5 | 31,522 | 5,586 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0403 | 13s |
| kna-5 | Plain | sonnet | 3 | yes | 4/5 | 31,272 | 4,660 | 4 | 0 | 2 | 3 | 0 | Grep | - | 0.0366 | 13s |
| tpl-1 | Plain | haiku | 1 | yes | 5/5 | 31,708 | 9,601 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0030 | 12s |
| tpl-1 | Plain | haiku | 2 | yes | 5/5 | 26,552 | 3,835 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0018 | 12s |
| tpl-1 | Plain | haiku | 3 | yes | 5/5 | 31,430 | 6,380 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0023 | 11s |
| tpl-1 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 30,638 | 7,937 | 3 | 3 | 0 | 1 | 0 | Grep+rm:show | 0 | 0.0024 | 13s |
| tpl-1 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 33,239 | 5,828 | 3 | 3 | 0 | 1 | 0 | Grep+rm:show | 0 | 0.0021 | 12s |
| tpl-1 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 32,325 | 5,674 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0021 | 12s |
| tpl-1 | RudhMap (nudged) | haiku | 1 | yes | 5/5 | 27,476 | 6,388 | 3 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0021 | 11s |
| tpl-1 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 27,520 | 2,909 | 3 | 4 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0015 | 11s |
| tpl-1 | RudhMap (nudged) | haiku | 3 | yes | 5/5 | 27,538 | 6 | 3 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0009 | 12s |
| tpl-1 | RudhMap-only | haiku | 1 | yes | 5/5 | 20,214 | 6,573 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0020 | 11s |
| tpl-1 | RudhMap-only | haiku | 2 | yes | 5/5 | 20,814 | 3,141 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0013 | 11s |
| tpl-1 | RudhMap-only | haiku | 3 | yes | 5/5 | 20,241 | 6 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0008 | 11s |
| tpl-1 | Plain | sonnet | 1 | no | 4/5 | 21,006 | 4,881 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-1 | Plain | sonnet | 2 | yes | 5/5 | 21,672 | 5,422 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0372 | 12s |
| tpl-1 | Plain | sonnet | 3 | yes | 5/5 | 21,242 | 5,041 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0351 | 12s |
| tpl-2 | Plain | haiku | 1 | yes | 3/4 | 26,983 | 5,666 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0023 | 13s |
| tpl-2 | Plain | haiku | 2 | yes | 3/4 | 26,916 | 4,926 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0021 | 13s |
| tpl-2 | Plain | haiku | 3 | yes | 3/4 | 26,769 | 4,912 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0020 | 14s |
| tpl-2 | RudhMap (natural) | haiku | 1 | yes | 3/4 | 29,225 | 5,764 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0023 | 14s |
| tpl-2 | RudhMap (natural) | haiku | 2 | yes | 3/4 | 29,207 | 4,994 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0021 | 13s |
| tpl-2 | RudhMap (natural) | haiku | 3 | yes | 3/4 | 29,193 | 4,954 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0022 | 14s |
| tpl-2 | RudhMap (nudged) | haiku | 1 | yes | 3/4 | 48,462 | 9,847 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0034 | 16s |
| tpl-2 | RudhMap (nudged) | haiku | 2 | yes | 3/4 | 47,481 | 9,154 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0031 | 15s |
| tpl-2 | RudhMap (nudged) | haiku | 3 | yes | 3/4 | 48,192 | 7,671 | 4 | 7 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0031 | 17s |
| tpl-2 | RudhMap-only | haiku | 1 | yes | 3/4 | 49,282 | 10,221 | 5 | 8 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0036 | 17s |
| tpl-2 | RudhMap-only | haiku | 2 | yes | 3/4 | 37,368 | 6,027 | 4 | 7 | 0 | 0 | 0 | rm:trace+rm:find_symbol | 0 | 0.0024 | 14s |
| tpl-2 | RudhMap-only | haiku | 3 | yes | 3/4 | 38,141 | 8,056 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0029 | 15s |
| tpl-2 | Plain | sonnet | 1 | yes | 3/4 | 23,173 | 5,012 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0347 | 12s |
| tpl-2 | Plain | sonnet | 2 | yes | 3/4 | 22,434 | 4,068 | 3 | 0 | 2 | 2 | 0 | Grep | - | 0.0329 | 13s |
| tpl-2 | Plain | sonnet | 3 | yes | 3/4 | 30,202 | 3,833 | 4 | 0 | 1 | 3 | 0 | Grep | - | 0.0324 | 14s |
| tpl-3 | Plain | haiku | 1 | yes | 5/5 | 81,964 | 14,477 | 5 | 0 | 4 | 4 | 1 | Grep+Glob | - | 0.0051 | 20s |
| tpl-3 | Plain | haiku | 2 | yes | 5/5 | 171,297 | 19,605 | 8 | 0 | 11 | 6 | 1 | Glob+Grep | - | 0.0079 | 32s |
| tpl-3 | Plain | haiku | 3 | yes | 5/5 | 92,925 | 19,611 | 5 | 0 | 10 | 3 | 1 | Glob+Grep | - | 0.0064 | 22s |
| tpl-3 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 80,138 | 15,302 | 5 | 1 | 4 | 5 | 0 | rm:find_symbol+Grep | 8 | 0.0051 | 19s |
| tpl-3 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 76,141 | 13,198 | 5 | 1 | 6 | 4 | 0 | rm:find_symbol+Grep | 9 | 0.0049 | 21s |
| tpl-3 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 126,640 | 15,748 | 7 | 2 | 6 | 5 | 0 | rm:find_symbol+rm:repo_map | 11 | 0.0058 | 22s |
| tpl-3 | RudhMap (nudged) | haiku | 1 | yes | 4/5 | 73,685 | 13,327 | 5 | 11 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0043 | 16s |
| tpl-3 | RudhMap (nudged) | haiku | 2 | yes | 4/5 | 69,764 | 7,436 | 5 | 10 | 0 | 2 | 0 | rm:find_symbol+rm:repo_map | 2 | 0.0034 | 18s |
| tpl-3 | RudhMap (nudged) | haiku | 3 | yes | 4/5 | 89,332 | 4,286 | 6 | 14 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0030 | 20s |
| tpl-3 | RudhMap-only | haiku | 1 | yes | 5/5 | 93,948 | 17,924 | 6 | 19 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0059 | 21s |
| tpl-3 | RudhMap-only | haiku | 2 | no | 3/5 | 64,225 | 8,881 | 5 | 12 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0036 | 18s |
| tpl-3 | RudhMap-only | haiku | 3 | no | 4/5 | 78,726 | 8,923 | 6 | 14 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0037 | 20s |
| tpl-3 | Plain | sonnet | 1 | yes | 4/5 | 23,221 | 4,296 | 3 | 0 | 3 | 3 | 0 | Grep | - | 0.0353 | 13s |
| tpl-3 | Plain | sonnet | 2 | yes | 5/5 | 46,363 | 5,839 | 5 | 0 | 3 | 7 | 0 | Grep | - | 0.0529 | 19s |
| tpl-3 | Plain | sonnet | 3 | yes | 4/5 | 38,592 | 5,892 | 4 | 0 | 3 | 3 | 0 | Grep | - | 0.0456 | 15s |
| tpl-4 | Plain | haiku | 1 | no | 3/5 | 45,603 | 8,162 | 4 | 0 | 4 | 2 | 1 | Grep+Glob | - | 0.0029 | 14s |
| tpl-4 | Plain | haiku | 2 | no | 3/5 | 28,690 | 5,268 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0020 | 10s |
| tpl-4 | Plain | haiku | 3 | no | 3/5 | 26,150 | 4,168 | 3 | 0 | 4 | 1 | 0 | Grep | - | 0.0019 | 12s |
| tpl-4 | RudhMap (natural) | haiku | 1 | no | 3/5 | 34,996 | 8,295 | 3 | 1 | 4 | 1 | 0 | rm:repo_map+Grep | 4 | 0.0027 | 13s |
| tpl-4 | RudhMap (natural) | haiku | 2 | no | 4/5 | 49,065 | 8,458 | 4 | 5 | 0 | 2 | 0 | rm:repo_map+Grep | 1 | 0.0029 | 14s |
| tpl-4 | RudhMap (natural) | haiku | 3 | no | 4/5 | 31,558 | 5,628 | 3 | 0 | 3 | 1 | 1 | Grep+Glob | - | 0.0020 | 12s |
| tpl-4 | RudhMap (nudged) | haiku | 1 | no | 3/5 | 50,334 | 9,388 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0032 | 15s |
| tpl-4 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 51,173 | 9,230 | 4 | 9 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0032 | 14s |
| tpl-4 | RudhMap (nudged) | haiku | 3 | no | 3/5 | 49,182 | 7,939 | 4 | 8 | 0 | 0 | 0 | rm:repo_map+rm:find_symbol | 0 | 0.0029 | 15s |
| tpl-4 | RudhMap-only | haiku | 1 | no | 3/5 | 27,160 | 7,901 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0025 | 12s |
| tpl-4 | RudhMap-only | haiku | 2 | no | 3/5 | 26,996 | 6,822 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0022 | 12s |
| tpl-4 | RudhMap-only | haiku | 3 | no | 3/5 | 27,249 | 6 | 3 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:repo_map | 0 | 0.0010 | 14s |
| tpl-4 | Plain | sonnet | 1 | no | 4/5 | 20,894 | 2,577 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0234 | 10s |
| tpl-4 | Plain | sonnet | 2 | no | 3/5 | 21,058 | 2,042 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0214 | 11s |
| tpl-4 | Plain | sonnet | 3 | no | 4/5 | 21,146 | 2,007 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0213 | 11s |
| tpl-5 | Plain | haiku | 1 | yes | 4/4 | 34,365 | 4,228 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0017 | 11s |
| tpl-5 | Plain | haiku | 2 | yes | 4/4 | 24,542 | 3,487 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0015 | 10s |
| tpl-5 | Plain | haiku | 3 | yes | 4/4 | 32,254 | 2,340 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0013 | 11s |
| tpl-5 | RudhMap (natural) | haiku | 1 | yes | 4/4 | 37,773 | 4,486 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0019 | 14s |
| tpl-5 | RudhMap (natural) | haiku | 2 | yes | 4/4 | 26,898 | 2,770 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0015 | 13s |
| tpl-5 | RudhMap (natural) | haiku | 3 | yes | 4/4 | 35,375 | 2,327 | 4 | 0 | 1 | 2 | 0 | Grep | - | 0.0014 | 12s |
| tpl-5 | RudhMap (nudged) | haiku | 1 | yes | 4/4 | 39,117 | 4,613 | 4 | 2 | 1 | 1 | 0 | Grep+rm:find_symbol | 1 | 0.0019 | 12s |
| tpl-5 | RudhMap (nudged) | haiku | 2 | yes | 3/4 | 37,080 | 2,812 | 4 | 2 | 0 | 2 | 0 | Grep+rm:find_symbol | 1 | 0.0014 | 11s |
| tpl-5 | RudhMap (nudged) | haiku | 3 | yes | 3/4 | 36,294 | 2,458 | 4 | 3 | 0 | 1 | 0 | Grep+rm:find_symbol | 0 | 0.0014 | 12s |
| tpl-5 | RudhMap-only | haiku | 1 | yes | 4/4 | 26,192 | 3,542 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0015 | 12s |
| tpl-5 | RudhMap-only | haiku | 2 | yes | 4/4 | 18,310 | 810 | 3 | 3 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0008 | 10s |
| tpl-5 | RudhMap-only | haiku | 3 | yes | 4/4 | 25,612 | 555 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0009 | 12s |
| tpl-5 | Plain | sonnet | 1 | yes | 4/4 | 20,133 | 2,649 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0207 | 9s |
| tpl-5 | Plain | sonnet | 2 | yes | 4/4 | 19,330 | 726 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0124 | 8s |
| tpl-5 | Plain | sonnet | 3 | yes | 4/4 | 20,168 | 1,953 | 3 | 0 | 1 | 1 | 0 | Grep | - | 0.0183 | 9s |
| httpx-1 | Plain | haiku | 1 | yes | 5/5 | 26,033 | 7,520 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0024 | 11s |
| httpx-1 | Plain | haiku | 2 | yes | 5/5 | 26,905 | 4,453 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0020 | 12s |
| httpx-1 | Plain | haiku | 3 | yes | 5/5 | 26,270 | 4,299 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0020 | 12s |
| httpx-1 | RudhMap (natural) | haiku | 1 | no | 3/5 | 32,834 | 9,227 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show | 0 | 0.0029 | 13s |
| httpx-1 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 33,235 | 9,225 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show | 0 | 0.0029 | 13s |
| httpx-1 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 32,304 | 5,911 | 3 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show | 0 | 0.0023 | 14s |
| httpx-1 | RudhMap (nudged) | haiku | 1 | yes | 5/5 | 21,791 | 9,213 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0027 | 11s |
| httpx-1 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 22,007 | 9,213 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0028 | 11s |
| httpx-1 | RudhMap (nudged) | haiku | 3 | yes | 5/5 | 22,097 | 4 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0011 | 12s |
| httpx-1 | RudhMap-only | haiku | 1 | yes | 5/5 | 17,056 | 9,017 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0026 | 12s |
| httpx-1 | RudhMap-only | haiku | 2 | yes | 5/5 | 16,959 | 4 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0009 | 11s |
| httpx-1 | RudhMap-only | haiku | 3 | yes | 5/5 | 16,969 | 4 | 2 | 6 | 0 | 0 | 0 | rm:show+rm:show+rm:show+rm:show+rm:show+rm:show | 0 | 0.0009 | 11s |
| httpx-1 | Plain | sonnet | 1 | yes | 5/5 | 22,637 | 6,151 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0398 | 12s |
| httpx-1 | Plain | sonnet | 2 | yes | 5/5 | 22,533 | 3,984 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0306 | 11s |
| httpx-1 | Plain | sonnet | 3 | yes | 5/5 | 22,562 | 3,659 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0291 | 11s |
| httpx-2 | Plain | haiku | 1 | yes | 5/5 | 16,231 | 2,578 | 2 | 0 | 0 | 2 | 0 | Grep+Grep | - | 0.0014 | 10s |
| httpx-2 | Plain | haiku | 2 | yes | 5/5 | 24,411 | 2,840 | 3 | 0 | 1 | 2 | 0 | Grep | - | 0.0016 | 11s |
| httpx-2 | Plain | haiku | 3 | yes | 4/5 | 25,656 | 3,159 | 3 | 0 | 3 | 2 | 0 | Grep+Grep | - | 0.0017 | 11s |
| httpx-2 | RudhMap (natural) | haiku | 1 | yes | 4/5 | 25,579 | 1,474 | 3 | 2 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0011 | 12s |
| httpx-2 | RudhMap (natural) | haiku | 2 | yes | 5/5 | 25,555 | 2,546 | 3 | 2 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0013 | 11s |
| httpx-2 | RudhMap (natural) | haiku | 3 | yes | 3/5 | 17,437 | 1,741 | 2 | 2 | 0 | 2 | 0 | rm:show+rm:trace+Grep+Grep | 0 | 0.0012 | 11s |
| httpx-2 | RudhMap (nudged) | haiku | 1 | yes | 4/5 | 25,497 | 2,425 | 3 | 2 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0012 | 11s |
| httpx-2 | RudhMap (nudged) | haiku | 2 | yes | 4/5 | 25,681 | 515 | 3 | 2 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0009 | 11s |
| httpx-2 | RudhMap (nudged) | haiku | 3 | yes | 4/5 | 25,577 | 575 | 3 | 2 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0008 | 10s |
| httpx-2 | RudhMap-only | haiku | 1 | yes | 3/5 | 18,740 | 2,589 | 3 | 3 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0012 | 12s |
| httpx-2 | RudhMap-only | haiku | 2 | yes | 3/5 | 19,038 | 1,958 | 3 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:trace | 0 | 0.0013 | 13s |
| httpx-2 | RudhMap-only | haiku | 3 | yes | 3/5 | 12,138 | 4 | 2 | 2 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0007 | 10s |
| httpx-2 | Plain | sonnet | 1 | yes | 5/5 | 14,828 | 3,232 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0246 | 10s |
| httpx-2 | Plain | sonnet | 2 | yes | 5/5 | 21,165 | 1,712 | 3 | 0 | 0 | 2 | 0 | Grep | - | 0.0195 | 11s |
| httpx-2 | Plain | sonnet | 3 | yes | 5/5 | 13,639 | 1,527 | 2 | 0 | 0 | 1 | 0 | Grep | - | 0.0160 | 8s |
| httpx-3 | Plain | haiku | 1 | yes | 4/5 | 62,789 | 9,533 | 5 | 0 | 6 | 3 | 1 | Grep+Glob | - | 0.0039 | 18s |
| httpx-3 | Plain | haiku | 2 | yes | 4/5 | 58,573 | 7,393 | 5 | 0 | 3 | 4 | 0 | Grep | - | 0.0032 | 17s |
| httpx-3 | Plain | haiku | 3 | yes | 4/5 | 44,462 | 6,707 | 4 | 0 | 2 | 4 | 0 | Grep | - | 0.0028 | 15s |
| httpx-3 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 48,448 | 9,119 | 4 | 2 | 0 | 4 | 0 | rm:find_symbol+Grep | 3 | 0.0032 | 16s |
| httpx-3 | RudhMap (natural) | haiku | 2 | yes | 4/5 | 43,765 | 5,675 | 4 | 2 | 1 | 3 | 0 | rm:find_symbol+Grep | 3 | 0.0026 | 16s |
| httpx-3 | RudhMap (natural) | haiku | 3 | yes | 4/5 | 32,354 | 7,057 | 3 | 2 | 1 | 1 | 0 | rm:find_symbol+Grep | 1 | 0.0026 | 13s |
| httpx-3 | RudhMap (nudged) | haiku | 1 | no | 3/5 | 61,107 | 9,506 | 5 | 4 | 0 | 1 | 0 | rm:find_symbol+rm:show | 1 | 0.0035 | 17s |
| httpx-3 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 44,889 | 5,878 | 4 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0026 | 16s |
| httpx-3 | RudhMap (nudged) | haiku | 3 | no | 3/5 | 43,326 | 4,674 | 4 | 4 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0021 | 14s |
| httpx-3 | RudhMap-only | haiku | 1 | no | 3/5 | 30,885 | 5,589 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0020 | 13s |
| httpx-3 | RudhMap-only | haiku | 2 | no | 4/5 | 31,613 | 1,381 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0014 | 14s |
| httpx-3 | RudhMap-only | haiku | 3 | yes | 5/5 | 33,641 | 5,710 | 4 | 9 | 0 | 0 | 0 | rm:find_symbol+rm:find_symbol | 0 | 0.0023 | 15s |
| httpx-3 | Plain | sonnet | 1 | yes | 4/5 | 38,241 | 5,157 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0428 | 16s |
| httpx-3 | Plain | sonnet | 2 | yes | 4/5 | 39,566 | 4,844 | 5 | 0 | 0 | 6 | 0 | Grep | - | 0.0413 | 16s |
| httpx-3 | Plain | sonnet | 3 | yes | 4/5 | 37,967 | 3,936 | 5 | 0 | 0 | 6 | 1 | Grep | - | 0.0383 | 16s |
| httpx-4 | Plain | haiku | 1 | yes | 4/5 | 34,209 | 7,691 | 3 | 0 | 2 | 1 | 0 | Grep+Read | - | 0.0026 | 11s |
| httpx-4 | Plain | haiku | 2 | yes | 4/5 | 28,767 | 5,920 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0024 | 13s |
| httpx-4 | Plain | haiku | 3 | yes | 5/5 | 28,127 | 5,326 | 3 | 0 | 2 | 2 | 0 | Grep+Grep | - | 0.0021 | 12s |
| httpx-4 | RudhMap (natural) | haiku | 1 | yes | 5/5 | 33,489 | 7,754 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0026 | 13s |
| httpx-4 | RudhMap (natural) | haiku | 2 | no | 3/5 | 30,451 | 4,908 | 3 | 3 | 0 | 1 | 0 | rm:find_symbol+Grep | 0 | 0.0019 | 12s |
| httpx-4 | RudhMap (natural) | haiku | 3 | yes | 5/5 | 33,727 | 7,009 | 3 | 1 | 2 | 1 | 0 | rm:find_symbol+Grep | 2 | 0.0025 | 14s |
| httpx-4 | RudhMap (nudged) | haiku | 1 | yes | 5/5 | 28,810 | 5,646 | 3 | 4 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0021 | 13s |
| httpx-4 | RudhMap (nudged) | haiku | 2 | yes | 5/5 | 44,699 | 5,839 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:trace | 0 | 0.0023 | 14s |
| httpx-4 | RudhMap (nudged) | haiku | 3 | yes | 5/5 | 45,987 | 2,302 | 4 | 4 | 0 | 1 | 0 | rm:show+rm:trace | 1 | 0.0018 | 15s |
| httpx-4 | RudhMap-only | haiku | 1 | no | 3/5 | 30,316 | 5,435 | 4 | 6 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0021 | 13s |
| httpx-4 | RudhMap-only | haiku | 2 | no | 4/5 | 30,572 | 2,798 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0015 | 13s |
| httpx-4 | RudhMap-only | haiku | 3 | no | 3/5 | 30,507 | 2,845 | 4 | 5 | 0 | 0 | 0 | rm:find_symbol+rm:show | 0 | 0.0016 | 14s |
| httpx-4 | Plain | sonnet | 1 | yes | 4/5 | 24,143 | 5,032 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0368 | 13s |
| httpx-4 | Plain | sonnet | 2 | yes | 5/5 | 25,897 | 5,843 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0425 | 15s |
| httpx-4 | Plain | sonnet | 3 | yes | 5/5 | 23,035 | 3,710 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0305 | 13s |
| httpx-5 | Plain | haiku | 1 | yes | 4/5 | 67,261 | 8,209 | 6 | 0 | 6 | 3 | 0 | Grep | - | 0.0035 | 18s |
| httpx-5 | Plain | haiku | 2 | yes | 4/5 | 68,436 | 10,893 | 5 | 0 | 6 | 2 | 0 | Grep | - | 0.0039 | 16s |
| httpx-5 | Plain | haiku | 3 | yes | 4/5 | 51,976 | 6,714 | 5 | 0 | 5 | 3 | 0 | Grep+Grep | - | 0.0030 | 17s |
| httpx-5 | RudhMap (natural) | haiku | 1 | yes | 3/5 | 40,799 | 5,460 | 4 | 6 | 2 | 0 | 0 | rm:show+rm:show+rm:show | 2 | 0.0025 | 15s |
| httpx-5 | RudhMap (natural) | haiku | 2 | yes | 3/5 | 40,386 | 5,361 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0022 | 14s |
| httpx-5 | RudhMap (natural) | haiku | 3 | no | 2/5 | 42,394 | 6,257 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0025 | 14s |
| httpx-5 | RudhMap (nudged) | haiku | 1 | yes | 3/5 | 41,861 | 7,539 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:show | 0 | 0.0026 | 14s |
| httpx-5 | RudhMap (nudged) | haiku | 2 | yes | 3/5 | 39,923 | 3,856 | 4 | 4 | 0 | 0 | 0 | rm:show+rm:show | 0 | 0.0019 | 14s |
| httpx-5 | RudhMap (nudged) | haiku | 3 | yes | 3/5 | 43,767 | 6,038 | 4 | 9 | 0 | 0 | 0 | rm:show+rm:show | 0 | 0.0025 | 14s |
| httpx-5 | RudhMap-only | haiku | 1 | yes | 3/5 | 43,496 | 7,454 | 5 | 5 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0028 | 16s |
| httpx-5 | RudhMap-only | haiku | 2 | yes | 3/5 | 32,015 | 5,606 | 4 | 9 | 0 | 0 | 0 | rm:show+rm:show | 0 | 0.0023 | 15s |
| httpx-5 | RudhMap-only | haiku | 3 | yes | 3/5 | 29,774 | 3,987 | 4 | 5 | 0 | 0 | 0 | rm:show+rm:find_symbol | 0 | 0.0019 | 14s |
| httpx-5 | Plain | sonnet | 1 | yes | 4/5 | 23,795 | 4,884 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0366 | 14s |
| httpx-5 | Plain | sonnet | 2 | yes | 4/5 | 23,507 | 3,933 | 3 | 0 | 3 | 1 | 0 | Grep | - | 0.0326 | 13s |
| httpx-5 | Plain | sonnet | 3 | yes | 4/5 | 22,104 | 3,247 | 3 | 0 | 2 | 1 | 0 | Grep | - | 0.0272 | 12s |

## Summary per setup

Per question the median of its 3 runs is taken, then the median across questions. A question counts as correct when at least 2 of its 3 runs are correct.

| Setup | Model | Correct questions | Correct runs | Median tokens / question | Median model calls | Median new content | Runs using RudhMap | RudhMap first | Built-in calls after RudhMap (mean) | Total $ |
|---|---|---|---|---|---|---|---|---|---|---|
| Plain | haiku | 12/15 | 37/45 | 31,430 | 3 | 5,458 | - | - | - | 0.12 |
| RudhMap (natural) | haiku | 13/15 | 36/45 | 35,375 | 4 | 5,828 | 36/45 | 35/45 | 2.0 | 0.11 |
| RudhMap (nudged) | haiku | 13/15 | 40/45 | 41,667 | 4 | 5,878 | 45/45 | 45/45 | 0.4 | 0.10 |
| RudhMap-only | haiku | 10/15 | 32/45 | 29,871 | 4 | 5,226 | 45/45 | 45/45 | 0.0 | 0.09 |
| Plain | sonnet | 12/15 | 36/45 | 23,507 | 3 | 4,204 | - | - | - | 1.50 |

## Step C pass criteria (eval/THRESHOLDS.md), Haiku

| Criterion | Target | Result | Pass |
|---|---|---|---|
| 1. Quality: correct questions >= plain Haiku | >= 12 | 13 | yes |
| 2. Cost: median tokens <= 0.7 x plain Haiku | <= 22,001 | 35,375 (113% of plain) | no |
| 3. No question plain gets right and RudhMap gets wrong in all 3 runs | none | none | yes |

## Tokens per question (median of 3 runs)

| Q | Plain haiku | RudhMap (natural) haiku | RudhMap (nudged) haiku | RudhMap-only haiku | Plain sonnet |
|---|---|---|---|---|---|
| kna-1 | 17,585 (0/3) | 26,675 (1/3) | 26,797 (2/3) | 12,600 (1/3) | 21,200 (0/3) |
| kna-2 | 55,689 (1/3) | 57,170 (2/3) | 51,186 (3/3) | 44,051 (2/3) | 40,731 (1/3) |
| kna-3 | 46,192 (3/3) | 59,858 (3/3) | 41,667 (3/3) | 34,057 (3/3) | 29,725 (3/3) |
| kna-4 | 28,362 (3/3) | 38,652 (3/3) | 38,820 (3/3) | 26,341 (3/3) | 30,057 (3/3) |
| kna-5 | 36,588 (3/3) | 38,448 (3/3) | 40,004 (3/3) | 29,871 (3/3) | 31,503 (3/3) |
| tpl-1 | 31,430 (3/3) | 32,325 (3/3) | 27,520 (3/3) | 20,241 (3/3) | 21,242 (2/3) |
| tpl-2 | 26,916 (3/3) | 29,207 (3/3) | 48,192 (3/3) | 38,141 (3/3) | 23,173 (3/3) |
| tpl-3 | 92,925 (3/3) | 80,138 (3/3) | 73,685 (3/3) | 78,726 (1/3) | 38,592 (3/3) |
| tpl-4 | 28,690 (0/3) | 34,996 (0/3) | 50,334 (1/3) | 27,160 (0/3) | 21,058 (0/3) |
| tpl-5 | 32,254 (3/3) | 35,375 (3/3) | 37,080 (3/3) | 25,612 (3/3) | 20,133 (3/3) |
| httpx-1 | 26,270 (3/3) | 32,834 (2/3) | 22,007 (3/3) | 16,969 (3/3) | 22,562 (3/3) |
| httpx-2 | 24,411 (3/3) | 25,555 (3/3) | 25,577 (3/3) | 18,740 (3/3) | 14,828 (3/3) |
| httpx-3 | 58,573 (3/3) | 43,765 (3/3) | 44,889 (1/3) | 31,613 (1/3) | 38,241 (3/3) |
| httpx-4 | 28,767 (3/3) | 33,489 (2/3) | 44,699 (3/3) | 30,507 (0/3) | 24,143 (3/3) |
| httpx-5 | 67,261 (3/3) | 40,799 (2/3) | 41,861 (3/3) | 32,015 (3/3) | 23,507 (3/3) |
