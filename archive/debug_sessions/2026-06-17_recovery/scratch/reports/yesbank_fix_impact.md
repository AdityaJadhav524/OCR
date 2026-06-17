# YES Bank Fix Impact Measurement

Total tokens split: **1**

| Page | Original Token | New Date Token | New Remainder Token | x0 | mid_x | x1 |
|------|----------------|----------------|---------------------|----|-------|----|
| 4 | `07/02/22UPI-HARPREET SINGH-` | `07/02/22` | `UPI-HARPREET SINGH-` | 78 | 183 | 431 |

## Conclusion

**CONCLUSION: The surgical fix split exactly 1 token.**
This directly recovers the single missing row without touching any valid date tokens.
Safe to implement as a token-preprocessing step inside `coordinate_parser_v2.py` or `row_detector.py`.