#include "my.h"
#include "mylib.h"

#include <stdio.h>

int main(void) {
#ifdef DEBUG
  puts("This is a debug version!");
#endif // DEBUG

  f();
  return 0;
}