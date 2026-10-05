
void FUN_00105780(int param_1)

{
  *(undefined4 *)(param_1 + 0x100) = 0;
  *(undefined4 *)(param_1 + 0x104) = 0;
  *(undefined4 *)(param_1 + 0x108) = 0;
  *(undefined4 *)(param_1 + 0x10c) = 0;
  *(undefined4 *)(param_1 + 0x110) = 0;
  *(undefined4 *)(param_1 + 0x114) = 0;
  if (*(int *)(param_1 + 0x118) != 0) {
    *(undefined4 *)(*(int *)(param_1 + 0x118) + 0x11c) = *(undefined4 *)(param_1 + 0x11c);
  }
  if (*(int *)(param_1 + 0x11c) != 0) {
    *(undefined4 *)(*(int *)(param_1 + 0x11c) + 0x118) = *(undefined4 *)(param_1 + 0x118);
  }
  if (param_1 == DAT_0029060c) {
    DAT_0029060c = *(int *)(param_1 + 0x118);
  }
  if (param_1 == DAT_00290610) {
    DAT_00290610 = *(int *)(param_1 + 0x11c);
    *(undefined4 *)(param_1 + 0x11c) = 0;
  }
  else {
    *(undefined4 *)(param_1 + 0x11c) = 0;
  }
  *(undefined4 *)(param_1 + 0x118) = 0;
  return;
}

