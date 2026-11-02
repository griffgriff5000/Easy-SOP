import pytest
from sop_capture.templates import appearance
from sop_capture.models import Project,Step
from sop_capture.screenshot_layout import screenshot_groups


def test_layout_defaults_legacy_and_validation():
    assert appearance()['screenshots_per_page']==0
    assert appearance({'page_per_step':True})['screenshots_per_page']==1
    assert not appearance({'page_per_step':True,'screenshots_per_page':0})['page_per_step']
    for count in (0,1,2,3,4,6):
        assert appearance({'screenshots_per_page':count,'screenshot_layout':'grid'})['screenshots_per_page']==count
    for values in ({'screenshots_per_page':5},{'screenshots_per_page':True},{'screenshot_layout':'unknown'},{'page_per_step':'invalid','screenshots_per_page':0}):
        with pytest.raises(ValueError):appearance(values)


def test_groups_count_images_without_losing_text_only_steps():
    steps=[Step(title=str(i),image='image.png' if i in (0,2,3,4) else None) for i in range(6)]
    groups=screenshot_groups(steps,appearance({'screenshots_per_page':2}))
    assert [[n for n,s in group] for group in groups]==[[1,2,3],[4,5,6]]
    assert all(sum(bool(s.image) for n,s in group)<=2 for group in groups)
