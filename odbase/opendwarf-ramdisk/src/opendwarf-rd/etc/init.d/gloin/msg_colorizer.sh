# /etc/init.d/thinit/msg_colorizer.sh functions -*- shell-script -*-
#
#
# examples:
#    log_begin_msg "setting your ip for ${INTERFACE}: $IP/$NETMASK"
#    ifconfig up  && echo "  $SUCCESS" || echo " failed "
#


setcolors() {

  # Reset fb color mode
  RESET="]R"
  # ANSI COLORS
  # Erase to end of line
  CRE="[K"
  # Clear and reset Screen
  CLEAR="c"
  # Normal color
  NORMAL="[0;39m"
  # RED: Failure or error message
  RED="[1;31m"
  # GREEN: Success message
  GREEN="[1;32m"
  # YELLOW: Descriptions
  YELLOW="[1;33m"
  # BLUE: System mesages
  BLUE="[1;34m"
  # MAGENTA: Found devices or drivers
  MAGENTA="[1;35m"
  # CYAN: Questions
  CYAN="[1;36m"
  # BOLD WHITE: Hint
  WHITE="[1;37m"

 SUCCESS=" ${BLUE}[ ${CYAN}ok ${BLUE}]${NORMAL}"
 FAILED=" ${NORMAL}[${RED}fail${NORMAL}]"

}

log_begin_msg () {
  echo -n " ${CYAN}*${NORMAL} $@"
}

log_warn_msg () {
  echo -n " ${YELLOW}*${NORMAL} $@"
}

log_error_msg () {
  echo -n " ${RED}*${NORMAL} $@"
}
