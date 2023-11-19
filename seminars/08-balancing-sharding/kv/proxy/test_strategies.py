from .strategies import raid3_join, raid3_split


def test_raid3_split():
    value = 'Hello, world!' # len = 13
    blocks = raid3_split(2, value) # 2 data blocks of 7 bytes, 1 parity block
    assert len(blocks) == 2

    assert blocks[0].index == 0
    assert blocks[0].data == b'Hello, '
    assert blocks[1].index == 1
    assert blocks[1].data == b'world!\x00'


def test_raid3_join_utf():
    value = 'съешь ещё этих мягких французских булок'
    blocks = raid3_split(4, value)
    assert len(blocks) == 4
    joined = raid3_join(blocks + [None])
    assert joined == value
