#include <stdio.h>

int main() {
#ifdef AMAZING
  printf("Amazing A!\n");
#elif defined(AWESOME)
  printf("Awesome A!\n");
#endif
}