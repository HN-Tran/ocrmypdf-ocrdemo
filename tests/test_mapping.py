"""Unit tests for ocrmypdf_docread.mapping."""

from ocrmypdf_docread.mapping import (
    build_ocr_tree_from_response,
    decompose_server_net_ccw,
    extract_net_angle_first_page,
    server_angle_to_deskew,
    server_angle_to_orientation,
)


def test_decompose_net_ccw():
    c, f = decompose_server_net_ccw(92.0)
    assert c == 90
    assert abs(f - 2.0) < 1e-6
    c2, f2 = decompose_server_net_ccw(0.0)
    assert c2 == 0 and f2 == 0.0


def test_server_angle_hooks():
    o = server_angle_to_orientation(90.0)
    assert o.angle == 90
    assert o.confidence == 15.0
    assert server_angle_to_deskew(92.0) == 2.0


def test_extract_net_angle():
    data = {"analyzeResult": {"pages": [{"angle": 3.5}]}}
    assert extract_net_angle_first_page(data) == 3.5


def test_build_tree_from_words():
    data = {
        "text": "Hello",
        "analyzeResult": {
            "pages": [
                {
                    "width": 100,
                    "height": 50,
                    "words": [
                        {
                            "content": "Hello",
                            "polygon": [0, 0, 50, 0, 50, 20, 0, 20],
                        }
                    ],
                }
            ]
        },
    }
    tree, text = build_ocr_tree_from_response(
        data, page_index=0, target_width=200, target_height=100, dpi=150.0
    )
    assert text == "Hello"
    assert tree.dpi == 150.0
    words = tree.words
    assert len(words) == 1
    assert words[0].text == "Hello"
    b = words[0].bbox
    assert b is not None
    assert b.left == 0 and b.top == 0
    assert b.right == 100 and b.bottom == 40
