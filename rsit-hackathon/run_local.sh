#!/usr/bin/env bash
set -euo pipefail

# 입력 파라미터(기본값 제공)
export AOI_NAME="${AOI_NAME:-ashburn}"    # ashburn | dublin | shanghai
export START_DATE="${START_DATE:-2023-07-15}"
export END_DATE="${END_DATE:-2023-07-15}"
export MAX_FILES="${MAX_FILES:-2}"

# AOI 좌표 프리셋
if [ "$AOI_NAME" = "ashburn" ]; then
  export BBOX="-77.6,38.85,-77.3,39.15"
elif [ "$AOI_NAME" = "dublin" ]; then
  export BBOX="-6.54,53.23,-6.02,53.48"
elif [ "$AOI_NAME" = "shanghai" ]; then
  export BBOX="121.0,31.0,121.8,31.6"
else
  echo "Unknown AOI_NAME=$AOI_NAME"; exit 1
fi

# 임시 폴더 및 출력 경로 설정
export DOWNLOAD_DIR="./tmp_data"
export OUTPUT_FILE="./docs/data/result.json"
mkdir -p "$DOWNLOAD_DIR" "$(dirname "$OUTPUT_FILE")"

# 파이썬 가상환경 활성화(필요 시 경로 수정)
PY=./.venv/bin/python

# 환경 변수 설정
export TIME_RANGE="$START_DATE,$END_DATE"

# 1) 임시 다운로드
echo "--- Running prepare_data.py ---"
$PY ./src/prepare_data.py

# 2) 처리 → 결과 JSON을 docs/data로
echo "\n--- Running process_data.py ---"
$PY ./src/process_data.py

# 3) 임시 데이터 정리(선택)
rm -rf "$DOWNLOAD_DIR"
echo "\nDONE: $OUTPUT_FILE updated for $AOI_NAME ($START_DATE..$END_DATE)"
