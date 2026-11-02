"""Shared screenshot grouping for generated Word and PDF content."""
def screenshot_groups(steps,settings):
    capacity=settings['screenshots_per_page'] or (4 if settings['screenshot_layout']=='grid' else 0)
    if settings['page_per_step'] and capacity==1:
        return [[(number,step)] for number,step in enumerate(steps,1)]
    groups=[];group=[];images=0
    for number,step in enumerate(steps,1):
        if capacity and step.image and images>=capacity:
            groups.append(group);group=[];images=0
        group.append((number,step));images+=bool(step.image)
    if group:groups.append(group)
    return groups


def layout_columns(settings):
    return 2 if settings['screenshot_layout']=='grid' and settings['screenshots_per_page']!=1 else 1
