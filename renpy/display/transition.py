import renpy
from renpy.display.render import render
import pygame
from pygame.constants import *

# This is a utility function that attempts to refactor an old and a new
# Fixed into four Fixeds: below, old, new, and above. Since only the
# old and new need transitions, this can be a significant win.
def refactor_fixed(in_old, in_new):

    Fixed = renpy.display.layout.Fixed

    out_below = Fixed()
    out_old = Fixed()
    out_new = Fixed()
    out_above = Fixed()

    if (not isinstance(in_old, Fixed)) or (not isinstance(in_new, Fixed)):
        return out_below, in_old, in_new, out_above

    old_list = in_old.get_widget_time_list()
    new_list = in_new.get_widget_time_list()

    # Merge the beginnings of the lists.
    while old_list and new_list:
        if old_list[0] == new_list[0]:
            out_below.add(new_list[0][0], new_list[0][1])
            old_list.pop(0)
            new_list.pop(0)

        else:
            break

    # Merge the ends of the lists.
    above_list = [ ]

    while old_list and new_list:
        if old_list[-1] == new_list[-1]:
            above_list.insert(0, new_list[-1])
            old_list.pop()
            new_list.pop()
        else:
            break

    for widget, time in above_list:
        out_above.add(widget, time)

    for widget, time in old_list:
        out_old.add(widget, time)

    for widget, time in new_list:
        out_new.add(widget, time)

    return out_below, out_old, out_new, out_above

class Transition(renpy.display.core.Displayable):
    """
    This is the base class of all transitions. It takes care of event
    dispatching (primarily by passing all events off to a SayBehavior.)
    """

    def __init__(self, delay):
        self.delay = delay
        self.offsets = [ ]
        self.events = True
        
    def event(self, ev, x, y):
        if self.events:
            return self.new_widget.event(ev, x, y)
        else:
            return None

class Fade(Transition):
    """
    This is a transition that involves fading to a certain color, then
    holding that color for a certain amount of time, then fading in the
    new scene.
    """

    def __init__(self, out_time, hold_time, in_time,
                 old_widget=None, new_widget=None, color=(0, 0, 0)):

        super(Fade, self).__init__(out_time + hold_time + in_time)

        self.out_time = out_time
        self.hold_time = hold_time
        self.in_time = in_time
        self.old_widget = old_widget
        self.new_widget = new_widget
        self.color = color

        # self.frames = 0

    # def __del__(self):
    #     print "Faded using", self.frames, "frames."

    def render(self, width, height, st):

        # self.frames += 1

        rv = renpy.display.render.Render(width, height)

        events = False

        if st < self.out_time:
            widget = self.old_widget
            alpha = int(255 * (st / self.out_time))

        elif st < self.out_time + self.hold_time:
            widget = None
            alpha = 255

        else:
            widget = self.new_widget
            alpha = 255 - int(255 * ((st - self.out_time - self.hold_time) / self.in_time))
            events = True

        if widget:
            surf = render(widget, width, height, st)
            
            rv.blit(surf, (0, 0))

        self.events = events 

        # Just to be sure.
        if alpha < 0:
            alpha = 0

        if alpha > 255:
            alpha = 255

        rv.fill(self.color[:3] + (alpha,))

        if st < self.in_time + self.hold_time + self.out_time:
            renpy.display.render.redraw(self, 0)

        return rv

# This was a nifty idea that just didn't work out, since we can't vary
# the alpha on an image with an alpha channel. Too bad.

# class Dissolve(Transition):

#     def __init__(self, time, old_widget, new_widget):
#         super(Dissolve, self).__init__(time)

#         self.time = time
#         self.below, self.old, self.new, self.above = refactor_fixed(old_widget, new_widget)

#     def event(self, ev, x, y):

#         rv = self.above.event(ev, x, y)

#         if rv is None:
#             rv = self.new.event(ev, x, y)

#         if rv is None:
#             rv = self.below.event(ev, x, y)
            
#         return rv
    
#     def render(self, width, height, st):

#         rv = renpy.display.render.Render(width, height)

#         # Below.
#         below = render(self.below, width, height, st)
#         rv.blit(below, (0, 0))

#         if st < self.time:
#             # Old.
#             old = render(self.old, width, height, st)
#             rv.blit(old, (0, 0))

#         # New.
#         alpha = min(255, int(255 * st / self.time))
#         new = render(self.new, width, height, st)

#         if alpha < 255:
#             surf = new.pygame_surface(False)
#             renpy.display.render.mutable_surface(surf)
#             surf.set_alpha(alpha, RLEACCEL)
#             rv.blit(surf, (0, 0))
#             rv.depends_on(new)
#         else:
#             rv.blit(new, (0, 0))

#         # Above.
#         above = render(self.above, width, height, st)
#         rv.blit(above, (0, 0))


#         if st < self.time:
#             renpy.display.render.redraw(self, 0)
        
#         return rv


        
class Dissolve(Transition):

    def __init__(self, time, old_widget=None, new_widget=None):
        super(Dissolve, self).__init__(time)

        self.time = time
        self.old_widget = old_widget
        self.new_widget = new_widget
        self.events = False

    def render(self, width, height, st):

        if st >= self.time:
            self.events = True
            return render(self.new_widget, width, height, st)

        rv = render(self.old_widget, width, height, st)

        top = render(self.new_widget, width, height, st)

        surf = top.pygame_surface(False)
        renpy.display.render.mutable_surface(surf)

        alpha = min(255, int(255 * st / self.time))


        surf.set_alpha(alpha, RLEACCEL)
        rv.blit(surf, (0, 0))

        if st < self.time:
            renpy.display.render.redraw(self, 0)

        return rv


class CropMove(Transition):
    """
    The CropMove transition works by placing the old and the new image
    on two layers, called the top and the bottom. (Normally the new
    image is on the top, but that can be changed in some modes.) The
    bottom layer is always drawn in full. The top image is first
    cropped to a rectangle, and then that rectangle drawn onto
    the screen at a specified position. Start and end crop rectangles
    and positions can be selected by the supplied mode, or
    specified manually. The result is a surprisingly flexible
    transition.

    This transition has many modes, simplifying its use. We can group
    these modes into three groups: wipes, slides, and other.

    In a wipe, the image stays fixed, and more of it is revealed as
    the transition progresses. For example, in "wiperight", a wipe from left to right, first the left edge of the image is
    revealed at the left edge of the screen, then the center of the image,
    and finally the right side of the image at the right of the screen.
    Other supported wipes are "wiperight", "wipedown", and "wipeup".

    In a slide, the image moves. So in a "slideright", the right edge of the
    image starts at the left edge of the screen, and moves to the right
    as the transition progresses. Other slides are "slideright", "slidedown",
    and "slideup".

    We also support a rectangular iris in with "irisin" and a
    rectangular iris out with "irisout". Finally, "custom" lets the
    user define new transitions, if these ones are not enough.
    """

    
    

    def __init__(self, time,
                 mode="fromleft",
                 startcrop=(0.0, 0.0, 0.0, 1.0),
                 startpos=(0.0, 0.0),
                 endcrop=(0.0, 0.0, 1.0, 1.0),
                 endpos=(0.0, 0.0),
                 topnew=True,
                 old_widget=None,
                 new_widget=None):

        """
        @param time: The time that this transition will last for, in seconds.
 
        @param mode: One of the modes given above.

        The following parameters are only respected if the mode is "custom". 

        @param startcrop: The starting rectangle that is cropped out of the
        top image. A 4-element tuple containing x, y, width, and height. 
        
        @param startpos: The starting place that the top image is drawn
        to the screen at, a 2-element tuple containing x and y.

        @param startcrop: The starting rectangle that is cropped out of the
        top image. A 4-element tuple containing x, y, width, and height. 
        
        @param startpos: The starting place that the top image is drawn
        to the screen at, a 2-element tuple containing x and y.

        @param topnew: If True, the top layer contains the new
        image. Otherwise, the top layer contains the old image.
        """
        

        self.time = time

        if mode == "wiperight":
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 0.0, 1.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "wipeleft":
            startpos = (1.0, 0.0)
            startcrop = (1.0, 0.0, 0.0, 1.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "wipedown":
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 0.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "wipeup":
            startpos = (0.0, 1.0)
            startcrop = (0.0, 1.0, 1.0, 0.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "slideright":
            startpos = (0.0, 0.0)
            startcrop = (1.0, 0.0, 0.0, 1.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "slideleft":
            startpos = (1.0, 0.0)
            startcrop = (0.0, 0.0, 0.0, 1.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "slideup":
            startpos = (0.0, 1.0)
            startcrop = (0.0, 0.0, 1.0, 0.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True
            
        elif mode == "slidedown":
            startpos = (0.0, 0.0)
            startcrop = (0.0, 1.0, 1.0, 0.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True

        elif mode == "slideawayleft":
            endpos = (0.0, 0.0)
            endcrop = (1.0, 0.0, 0.0, 1.0)
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = False

        elif mode == "slideawayright":
            endpos = (1.0, 0.0)
            endcrop = (0.0, 0.0, 0.0, 1.0)
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = False

        elif mode == "slideawaydown":
            endpos = (0.0, 1.0)
            endcrop = (0.0, 0.0, 1.0, 0.0)
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = False
            
        elif mode == "slideawayup":
            endpos = (0.0, 0.0)
            endcrop = (0.0, 1.0, 1.0, 0.0)
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = False

        elif mode == "irisout":
            startpos = (0.5, 0.5)
            startcrop = (0.5, 0.5, 0.0, 0.0)
            endpos = (0.0, 0.0)
            endcrop = (0.0, 0.0, 1.0, 1.0)
            topnew = True
            
        elif mode == "irisin":
            startpos = (0.0, 0.0)
            startcrop = (0.0, 0.0, 1.0, 1.0)
            endpos = (0.5, 0.5)
            endcrop = (0.5, 0.5, 0.0, 0.0)
            topnew = False
            
            
        elif mode == "custom":
            pass
        else:
            raise Exception("Invalid mode %s passed into boxwipe." % mode)

        self.delay = time
        self.time = time

        self.startpos = startpos
        self.endpos = endpos

        self.startcrop = startcrop
        self.endcrop = endcrop
        
        self.topnew = topnew

        self.old_widget = old_widget
        self.new_widget = new_widget

        self.events = False

        if topnew:
            self.bottom = old_widget
            self.top = new_widget
        else:
            self.bottom = new_widget
            self.top = old_widget

    def render(self, width, height, st):

        time = 1.0 * st / self.time

        # Done rendering.
        if time >= 1.0:
            self.events = True
            return render(self.new_widget, width, height, st)
        
        # How we scale each element of a tuple.
        scales = (width, height, width, height)

        def interpolate_tuple(t0, t1):
            return tuple([ s * (a * (1.0 - time) + b * time)
                           for a, b, s in zip(t0, t1, scales) ])

        crop = interpolate_tuple(self.startcrop, self.endcrop)
        pos = interpolate_tuple(self.startpos, self.endpos)

        rv = renpy.display.render.Render(width, height)

        rv.blit(render(self.bottom, width, height, st), (0, 0))

        top = render(self.top, width, height, st)
        rv.blit(top.subsurface(crop), pos)

        renpy.display.render.redraw(self, 0)
        return rv
                
            
