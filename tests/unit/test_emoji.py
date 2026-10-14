from media_bot.services.emoji import sticker_set_name, tile_hash


def test_tile_hash_is_stable_and_names_never_contain_user_text() -> None:
    assert tile_hash(b"tile") == tile_hash(b"tile")
    name = sticker_set_name(42, 1, "PhantasyBot")
    assert name == "pb_42_1_by_PhantasyBot"
    assert name.endswith("Bot")


def test_sticker_set_name_normalizes_bot_suffix() -> None:
    assert sticker_set_name(7, 2, "my-bot").endswith("mybot")
