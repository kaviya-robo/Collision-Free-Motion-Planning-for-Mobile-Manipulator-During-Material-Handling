#!/usr/bin/env bash
# Make the official turtlebot3_manipulation stack (Gazebo, MoveIt 2 + OMPL, Nav2) use the
# industrial geometry. The official launch files hard-code
#   turtlebot3_manipulation_description/urdf/turtlebot3_manipulation.urdf.xacro
# so this script backs that file up and replaces it with our drop-in xacro.
#
#   usage:   ./use_with_turtlebot3_manipulation.sh  ~/turtlebot3_ws        (install)
#            ./use_with_turtlebot3_manipulation.sh  ~/turtlebot3_ws --undo (restore official)
set -e
WS="${1:-$HOME/turtlebot3_ws}"
DESC="$WS/src/turtlebot3_manipulation/turtlebot3_manipulation_description/urdf"
TOP="$DESC/turtlebot3_manipulation.urdf.xacro"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "$TOP" ]; then
  echo "Official package not found at $DESC"
  echo "Clone it first:  cd $WS/src && git clone -b humble https://github.com/ROBOTIS-GIT/turtlebot3_manipulation.git"
  exit 1
fi

if [ "$2" == "--undo" ]; then
  cp "$TOP.official.bak" "$TOP"
  echo "Restored the official xacro."
else
  [ -f "$TOP.official.bak" ] || cp "$TOP" "$TOP.official.bak"
  cp "$HERE/urdf/tb3_omx.urdf.xacro" "$TOP"
  echo "Installed industrial xacro (backup: $TOP.official.bak)."
fi
echo "Now rebuild:  cd $WS && colcon build --symlink-install && source install/setup.bash"
