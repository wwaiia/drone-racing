"""Self-test for the Telegram web collector using a local fixture of the t.me/s markup."""
import sys
sys.path.insert(0, ".")

from unittest.mock import patch

import app.collectors.telegram_web as tw

FIXTURE = """
<html><body>
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" data-post="fpv_races/101">
  <div class="tgme_widget_message_bubble">
    <div class="tgme_widget_message_text js-message_text">
      24 ноября 2026 года в 10:00 Липецк: открытые региональные соревнования по дрон-рейсингу.
      Регистрация открыта — https://forms.gle/abc. Призовой фонд 100 000 ₽.
    </div>
    <time datetime="2026-11-01T10:00:00+00:00"></time>
  </div>
</div></div>
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" data-post="fpv_races/102">
  <div class="tgme_widget_message_bubble">
    <div class="tgme_widget_message_text">
      21.11.2026 в 12:30 Воронеж: гонки FPV-дронов, парковка ВГТУ-Аэро.
      Регистрация открыта по ссылке forms.yandex.ru/vrn. Призовой фонд уточняется.
    </div>
    <time datetime="2026-11-02T09:00:00+00:00"></time>
  </div>
</div></div>
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" data-post="fpv_races/103">
  <div class="tgme_widget_message_bubble">
    <div class="tgme_widget_message_text">
      <video>Короткое видео с прошлой гонки</video>
    </div>
    <time datetime="2026-11-03T09:00:00+00:00"></time>
  </div>
</div></div>
</body></html>
"""


class FakeResp:
    text = FIXTURE

    def raise_for_status(self):
        pass


def test_fetch():
    with patch.object(tw.httpx, "get", return_value=FakeResp()):
        posts = tw.fetch_channel_posts("fpv_races", limit=10)
    assert len(posts) == 2, f"expected 2 posts (post 3 is short video -> filtered), got {len(posts)}"
    p1 = posts[0]
    assert p1["id"] == "101"
    assert p1["url"] == "https://t.me/fpv_races/101"
    assert "24 ноября 2026" in p1["text"]
    assert p1["date"] == "2026-11-01T10:00:00+00:00"
    return posts


def test_ingest(posts):
    with tw.SessionLocal() as session:
        evt = tw.ingest_post(
            session, text=posts[0]["text"], platform="telegram",
            source_title="tg:fixture_test", external_post_id="fixture-101-unique",
            auto_approve=True,
        )
        assert evt is not None, "event should be created from fixture post"
        print(f"OK event: id={evt.id} date={evt.event_date} region={evt.region.name if evt.region else None} "
              f"status={evt.status} prize={evt.prize_fund_amount} type={evt.event_type}")
        assert str(evt.event_date) == "2026-11-24"
        assert evt.region is not None and "Липецк" in evt.region.name
        assert evt.status == "registration_open"
        assert evt.prize_fund_amount == 100000


if __name__ == "__main__":
    posts = test_fetch()
    print("FETCH OK")
    test_ingest(posts)
    print("INGEST OK")
    print("TELEGRAM_WEB SELFTEST: PASS")
