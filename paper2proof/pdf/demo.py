"""Original demonstration text, never represented as a research publication."""


def demo_pdf() -> bytes:
    import pymupdf

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((60, 60), "Paper2Proof engineering demonstration", fontsize=18)
        page.insert_text((60, 100), "This document is a test fixture, not a research paper.")
        page.insert_text(
            (60, 130),
            "Randomized Kaczmarz is tested against a relative L2 solution error target of 0.01.",
        )
        page.insert_text(
            (60, 160),
            "The fixture uses synthetic data: 128 rows, 32 columns, and zero initialization.",
        )
        page.insert_text(
            (60, 190), "Run 512 updates with seeds 7, 23, 41. These are engineering settings."
        )
        page.insert_text(
            (60, 220), "The target is an explicit test policy, not a published scientific finding."
        )
        return document.tobytes()
