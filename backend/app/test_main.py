import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from pathlib import Path
from dotenv import load_dotenv

# conf/.envから環境変数を読み込み
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / "conf" / ".env")


@pytest.fixture(autouse=True)
def set_real_mode(monkeypatch):
    monkeypatch.setenv("BACKEND_MODE", "real")


# def test_qwen_local_inference():
#     # Qwenモデルのローカル推論テスト
#     from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
#     model_path = Path(__file__).parent.parent / "models" / "qwen-0.5b"
#     tokenizer = AutoTokenizer.from_pretrained(model_path)
#     model = AutoModelForCausalLM.from_pretrained(model_path).eval()
#     qwen_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
#     SYSTEM_PROMPT = "あなたは日本語から中国語に翻訳された文を校閲するプロフェッショナルです。中国語で回答のみを出力してください。次の例にしたがって、日本語から中国語へ翻訳を試みた文を対象に、中国語で原文の意味から誤っている箇所を５つ指摘し、中国語で全体講評を行ってください。ただし、次の回答形式の条件を満たすこと。"
#     FEW_SHOT_EXAMPLES = """
#     ## 翻訳の指摘の例
#     ＜中国語に翻訳する日本語の文＞筆者は以前、早期教育の幼児教室で働いていたことでした。保護者からよく「この教室に通わせたらどのような大人になるのか」と聞かれました。答えようがありませんでした。大人になるのは様々な要因が積み重なり絡み合ったことです。遺伝、家庭環境、友達及びどんな担任にあったかなどです。

#     授業中、小さな子をいじめるなど問題行為を起こす子供がいました。お母親がお迎えにいらした時そのことを伝えました。「でもうちの子は文字と数字が大好きで、お勉強ができるんだ」と反論されました。優秀だと思っていた我が子を指摘されて、気分を害したかもしれない。「幼い頃算盤をやらせて計算能力が高くなった」とか「幼い頃絵本を沢山読み聞かせたから、読書家となり国語成績がよくなった」など、一定の側面は程度の結果が出るが、「勉強ができるかできないか」と「人としてやって悪いことよいことを教育する」は別次元のことからです。

#     「十で神童十五で才子二十過ぎればただの人」ということわざがあります。
#     「幼い頃並外れて優れているように見えるが、多くは成長につれて平凡な人となってしまう」のたとえです。それを使って、早期教育をしている人を批判する人もいます。勉強ができるかどうかだけで、そればかりに目を奪われて評価で子育てをしていると、学歴があっても社会に出て問題行為を起こすかもしれません。

#     東大に入学して、エリートになる人もいれば、罪をした人もいる。高校中退してニートになる人もいれば、社会貢献して偉業をなす人もいる。
#     「東大出身だから・・・高校中退だから・・・」という因果関係はない。人としてどうなるかのスタートは、子供時代に親から受けた教えと愛情、友達関係とどんな担当にあったなどです。混同しないようにしましょう。

#     ＜日本語の文から中国語に翻訳を試みた文＞笔者以前=辻早教班的老姉。学生家本経常向我"在个班学，我家孩子会変成怎祥的大人呢？"我并不想回复。成为大人是由各种原因纵横交错而成，比方说遗传、家庭环境、友情以及工作等因素。

#     在我的课上，有个孩子霸凌年纪比较小的孩子。这个孩子妈妈来接他的时候，我将这件事告诉这孩子的妈妈。或许这位妈妈听完我讲的话心情不好受，想着我竟然去批评她那么优秀的孩子。反驳我道："我家孩子非常喜欢文字和数字，学习可厉害了。"虽然，"从小就让孩子学算盘所以孩子计算能力很强"、"从小就让孩子看很多绘本，作为阅读小能手语文成绩很好。"这些从一定的侧面来说早教是有所成果的。但是这些和"会不会学习"、"教育孩子作为人哪些可＊哪些不可"来説完全是两事

#     有句語叫"小日アア、大未必佳。"返句活指的是那些小候卓越非凡的人，大部分在成的
#     辻程中都変成普通人。有人用句活去批判行早教的人。単凭学成績，只用成績来价教
#     育孩子成功与否，即便孩子有学，走上社会可能也会出某些題。

#     同様考上大，有的人成精英，有的人成犯罪分子。高中退学的人群中，有的人老，有
#     的人奉献社会成就个人伟业。这些都和东大毕业、高中退学没有任何关系。生而为人会成为什么，其出发点在于孩童时期接受到的家庭教育、爱情、友情和工作。请不要将两者混为一谈

#     ＜日本語の文から中国語に翻訳を試みた文に対する誤りの指摘＞
#     1.我并不想回复
#     ようがない并非不想的含义，这里可以再看一下这个文法的含义
#     ようがない：〜できない / 〜したくても手段がない
#     不可能であることを強調して言う時に使う。

#     2.どんな担任にあったか
#     担任指的是学校的老师哦
#     担任：学校で，教師があるクラス・教科などを受け持つこと。また，その教師。

#     3.有个孩子霸凌年纪比较小的孩子
#     这里最好把問題行為译出来哦

#     译文整体的流畅性和对原意翻译处理和展现比较不错，可以再看一下以上几点，注意积累一下ようがない和担任的含义，加油～
#     """
#     originalText = (
#         "近年は地政学リスクの高まりの中で、日本企業は中国を念頭に生産拠点の脱中国化を進める対中デリスキングの流れがあった。"
#         "次は、輸出先をアメリカから転換していく動きも徐々に出てこよう。米国市場の重要性は変わらないものの、対米輸出依存度を下げ、"
#         "地域分散によるリスク低減を図る企業が増加するだろう。特にASEANやインドなど成長市場への展開を模索する動きが予想される。"
#         "大学は、かつての高度経済成長期における第 1 次ベビーブームによる 18 歳人口の激増と社会からの高等教育の拡大要請、"
#         "設置認可の緩和などを経て、大学数、学生数を飛躍的に増大させてきた。大学は、それまでの\"アカデミズムの最高府\""
#         "(高等教育の発達段階における「エリ－ト型」段階)から、急速に\"大衆化\"(「マス型」段階)へと変貌した。"
#         "その後、経済成長の減速や少子化といった大学環境を取り巻くマイナス要因が続く中で、大学は依然として大学数、定員を増やし、"
#         "ついに高等教育の発達段階の最終ステージである「ユニバーサル型」段階(進学率 50％以上)を目前にしている"
#         "(20 年度大学進学率 49.1％。短大を含めた 20 年度進学率は 55.3％)。"
#     )
#     targetText = "近年来，随着地缘政治风险高涨，日企提出对华\"去风险\"，计划以中国为起点逐渐将生产线撤离中国。"
#     instructionPrompt = "## 条件\n- 指摘例の回答形式の構造・分量に従う\n- 全体講評の口調・分量に従う\n- 全体講評は、「加油〜」で終える"
#     prompt = f"{SYSTEM_PROMPT}\n{instructionPrompt}\n{FEW_SHOT_EXAMPLES}\n原文: {originalText}\n添削対象: {targetText}\n## あなたが生成する回答 \n＜日本語の文から中国語に翻訳を試みた文に対する誤りの指摘＞"
#     result = qwen_pipe(prompt, max_new_tokens=512, do_sample=True)[0]["generated_text"]
#     print("[Qwen local inference raw result]", result)
#     assert isinstance(result, str)
#     assert len(result) > 0


# def test_generate_suggestions_real_qwen():
#     payload = {
#         "originalText": "今日は天気がいいです",
#         "targetText": "今日は天気が良いです",
#         "instructionPrompt": "丁寧な日本語に直してください",
#         "sessionId": "test-session"
#     }
#     with TestClient(app) as client:
#         response = client.post("/suggestions", json=payload)
#         assert response.status_code == 200
#         data = response.json()
#         # モックのoverallCommentと異なること（必要に応じて）
#         assert data["overallComment"] != "全体的に日本語の表現が自然になり、より丁寧で適切な文章になりました。特に敬語の使い方と助詞の選択が改善されています。"
#         # suggestionsがlist型であること（空でもよい）
#         assert isinstance(data["suggestions"], list)


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_generate_suggestions_gemini():
    payload = {
        "originalText": "今日は天気がいいです",
        "targetText": "今日は天気が良いです",
        "instructionPrompt": "丁寧な日本語に直してください",
        "sessionId": "test-session-gemini",
        "engine": "gemini"
    }
    with TestClient(app) as client:
        response = client.post("/suggestions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "overallComment" in data
        assert isinstance(data["suggestions"], list)
        # 新しい形式では指摘箇所のみなので、originalとreasonが存在する
        if len(data["suggestions"]) > 0:
            suggestion = data["suggestions"][0]
            assert "original" in suggestion
            assert "reason" in suggestion 