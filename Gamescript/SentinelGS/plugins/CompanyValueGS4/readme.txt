Company Value GS
================

Company Value GS is a Game Script that uses the goal list to rank
companies by their current company value. It can also be used to challenge
companies not only to be the first to reach a user defined company value
target as a goal, but also to do it as fast as they can.


Configuration Settings
----------------------

Goal mode:
- Only rank companies by their values:
    In this mode, Company Value GS only uses the goal list window to rank
    companies by their current company value. The value of the most
    valuable company is used to determine the progress of every company
    in relation to it. No goal is assigned to any company.

- Reach target company value below:
    In this mode, Company Value GS uses the goal list window to also rank
    companies by their current value. The target value, which is set on
    the next setting, is used to determine the progress of every company
    in relation to it. Each company is given the same challenge, to become
    the first to reach the target value. Once reached, Company Value GS
    pauses the game and informs every company of the winner and the time
    it took to reach it since its inauguration, while asking if they want
    to continue playing. The moment any company continues playing, the
    game is unpaused and Company Value GS switches Goal mode to ranking
    mode.

Target company value (in thousand £):
- Sets the value companies need to reach. Used when Goal mode is set to
  reach this target value. Has no effect when Goal mode is set to ranking
  mode.
  
Amount of debug messages to log:
- Essential:
    Logs only the minimum necessary, when Company Value GS is reaching key
    points, such as pausing the game, reaching the goal, switching game
    mode.

- Normal:
    Also logs minimum details for loading, saving, starting, initializing,
    opening and closing of questions, and changes to the target company
    value.

- Too many:
    Logs more details for loading, saving, starting and initializing. Also
    logs creation and removal of company goal details during Goal mode.

- Insane:
    Logs every internal variable changes and every goal computations in
    near real time.

AI-GS communication support:
- Enable to allow Company Value GS to communicate with AI companies via 
  signs, by using the Script Communication Protocol (SCP).