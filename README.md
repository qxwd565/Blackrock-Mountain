# Blackrock Mountain card API

검은바위 산의 한국어 정규/야생 카드 데이터입니다. 날짜 기준은 Asia/Seoul입니다.

## 편집 형식

- `data/<CARD_ID>.json`의 첫 날짜 키(`YYYY-MM-DD`)에는 최초 플레이 가능한 시점의 스펙을 저장합니다. 원본 `schemaVersion: 2` 자료는 `metadata/<CARD_ID>.json`의 `originalSource`에 보존합니다.
- `card.releasedAt`에 최초 날짜를 적고 `card.patches`에는 그 이후 실제 변경분만 날짜순으로 기록합니다. 현재와 같아도 최초 숫자는 생략하지 않습니다.
- 출시 문구·이름·희귀도 연혁이 완전히 확인되지 않은 카드는 `initialSpecStatus: partially_verified`입니다. 당시 원문과 미확정 구간은 `historicalTextObservations`, `tools/brm-release-audit.json`에서 확인하세요. 현재 문구를 출시 원문이라고 인증하지 않습니다.
- 표시 문자열의 줄바꿈은 `<br></br>`입니다. `nativeTags`, `nativeRawText`, 원시 관측의 줄바꿈은 변환하지 않습니다.
- `nativeTags`와 `nativeRawText`는 설치된 클라이언트의 원본 증거이며 과거 날짜의 스펙이 아닙니다.

## 한국 출시 기준

보유 가능한 모험 보상/직업 도전의 한국 개방일을 사용합니다. 1~5지구는 각각 2015-04-03, 04-10, 04-17, 04-24, 05-01입니다. 클라이언트에 먼저 들어온 날이나 북미 게시일, 투기장 미리보기와 섞지 않습니다.

생성 카드와 선택지는 실제 생성 경로를 확인합니다. 판드랄 합체형 `OG_044b`는 2015년 카드가 아니며 고대 신의 속삭임 한국 출시일인 2016-04-27부터입니다. 우연한 미리보기/잠금 카드 무작위 생성 가능성까지 출시 기준으로 삼지는 않습니다.

## 생성과 검사

```sh
python3 tools/build-api.py
python3 tools/test-brm-history.py
```

- `cards.json`: 현재값 목록
- `render.json`: 현재값과 날짜 조회용 역방향 이력
- `history.json`: 이전 소비자를 위한 호환 이력

생성 파일을 직접 고치지 말고 원본 JSON을 수정한 뒤 빌드하세요. 빌더는 저장소에 커밋된 코드만 실행합니다. CI는 읽기 전용이며 외부 스크립트 다운로드나 자동 커밋/푸시를 하지 않습니다.

검증 범위와 남은 한계는 [감사 기록](AUDIT.md), 카드별 근거는 `tools/brm-release-audit.json`에 있습니다.

## Date-first canonical data

Card-specific files now use ascending Korean date keys with explicit field-removal semantics. See [docs/date-schema.md](docs/date-schema.md) for the dual root transports, preserved source evidence, bounded historical uncertainty and reproducible checks. Existing schema1 plugin endpoints remain unchanged in purpose; precise clients must explicitly select the `*-date.json` siblings.

## 2026-11-13 최초 사용일 전수 재검증

[41개 카드별 최초 출시일·생성 경로 검증](tools/brm-first-use-verification-20261113.json)에서 한국 5지구 개방 보상 31개와 생성·선택지·영웅/영웅 능력 9개, 2016년 판드랄 합체형 `OG_044b` 1개를 각각 대조했습니다. 공식 블리자드 보상/출시 공지와 당시 한국 보도 날짜를 교차 검증했으며, 41개 모두 기존 최초 사용일과 일치합니다. 3·4지구의 해외 기준 전날 기사 날짜는 한국 개방일로 소급하지 않았습니다. 기존 밸런스 날짜, 카드 원본, 토큰 ID, 아트 및 플러그인 연결은 변경하지 않았습니다.

원본 생성 관계(`relatedIds`) 9개를 실제 DBF ID로 검사하고, 판드랄 합체형은 고대 신 출시 `2016-04-27`이라는 별도 생성 조건을 확인합니다. `python3 tools/test-brm-first-use.py`를 GitHub Actions 검증 단계에 추가했습니다.
