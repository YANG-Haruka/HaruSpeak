from __future__ import annotations

from ..base import ErrorPattern, ErrorPatternLib


_PATTERNS: dict[str, list[ErrorPattern]] = {
    "zh": [
        ErrorPattern(
            symptom="把粤语的 6 声硬套到普通话的 4 声，T2 和 T5 / T3 和 T6 不分",
            cause="普通话只有 4 声，缺低升 (T5)、低平 (T6) 这种低音区对立",
            hint="T5 是从低位往上微抬（廿 jaa6 vs 廿一 jaa6jat1 里那个 jaa6 不对，应该 jaa6 = 6），T2 是从中位往高位明显上扬",
        ),
        ErrorPattern(
            symptom="-p / -t / -k 入声尾发出明显的元音",
            cause="普通话音节只能以元音或 -n / -ng 收尾，没有塞音入声",
            hint="入声字（如「食」sik6）末尾要急停，闭口/抵舌/顶喉，但**不要**送气、不要带元音",
        ),
        ErrorPattern(
            symptom="圆唇前元音 yu (/y/) 念成普通话 ü 或 i",
            cause="粤语 yu 类似德语 ü，比普通话 ü 更紧",
            hint="圆唇程度比普通话 ü 更明显，舌位更靠前一点",
        ),
    ],
    "en": [
        ErrorPattern(
            symptom="Six-tone system flattened to two or three pitch levels",
            cause="English uses pitch for emphasis, not lexical contrast",
            hint="Distinguish T1 (high steady) vs T3 (mid steady) vs T6 (low steady) without changing loudness",
        ),
        ErrorPattern(
            symptom="Releasing final -p/-t/-k stops audibly with a vowel",
            cause="English speakers tend to release final consonants",
            hint="In sik6 (食), close the mouth at /k/ and stop airflow — no 'kuh' sound after",
        ),
        ErrorPattern(
            symptom="Pronouncing 'oe' (/œ/) as English 'er' or 'aw'",
            cause="English lacks the front-rounded mid vowel /œ/ in 靴 hoe1",
            hint="Round lips like /o/ but keep tongue forward as for /e/",
        ),
    ],
    "ja": [
        ErrorPattern(
            symptom="6 声をすべてフラットに発音し、特に T2 と T5 を区別できない",
            cause="日本語のピッチアクセントは語レベルの上下、広東語は音節ごとの絶対音高",
            hint="T2 は中→高への明確な上昇、T5 は低→中への控えめな上昇。両方上がるが幅と起点が違う",
        ),
        ErrorPattern(
            symptom="-p / -t / -k の入声を促音「っ」で代用してしまう",
            cause="日本語の促音は次子音への準備、広東語の入声は閉鎖のみ",
            hint="食 (sik6) の最後は息を完全に止めるだけ、次の音は来ない",
        ),
        ErrorPattern(
            symptom="広東語の長短母音 (aa vs a) を区別せず、すべて短く発音する",
            cause="日本語の母音長は語彙対立を持たないことも多い",
            hint="街 gaai1 と 雞 gai1 は長さと音色が違う — aa は明確に長く、口を大きく開ける",
        ),
    ],
    "ko": [
        ErrorPattern(
            symptom="평음·격음·경음의 삼항 대립을 광둥어 성조에 매핑하려 함",
            cause="광둥어는 송기 여부보다 성조가 의미를 결정",
            hint="광둥어 자음은 송기 여부만 구별 (p vs ph 등). 성조에 집중",
        ),
        ErrorPattern(
            symptom="입성 -p / -t / -k 을 한국어 받침처럼 모음 후행으로 발음",
            cause="한국어 받침은 음절 끝에서 약하게 닫히지만 광둥어 입성은 더 단호함",
            hint="식 (食 sik6) 의 끝에서 입을 완전히 다물고 소리를 끊는다",
        ),
        ErrorPattern(
            symptom="6 성을 4-5 개로 줄여 발음",
            cause="대부분의 학습자가 T2 ↔ T5, T3 ↔ T6 을 합쳐 듣고 발음함",
            hint="저음역의 평성/상승 대립 (T6 vs T5) 을 의식적으로 구별 연습",
        ),
    ],
}


def common_errors(l1: str) -> ErrorPatternLib:
    return ErrorPatternLib(l1=l1, l2="yue", patterns=_PATTERNS.get(l1, []))
