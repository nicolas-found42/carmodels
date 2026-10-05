
void FUN_001055e8(int param_1)

{
  if (*(int *)(param_1 + 0x104) != 0) {
    if (*(int *)(param_1 + 0x108) == 0) {
      *(undefined4 *)(param_1 + 0x110) = 0;
      *(undefined4 *)(param_1 + 0x10c) = 1;
      FUN_0010d560();
    }
    *(undefined4 *)(param_1 + 0x10c) = 1;
    *(undefined4 *)(param_1 + 0x108) = 1;
    *(undefined4 *)(param_1 + 0x104) = 1;
    return;
  }
  *(undefined4 *)(param_1 + 0x10c) = 1;
  *(undefined4 *)(param_1 + 0x108) = 1;
  *(undefined4 *)(param_1 + 0x104) = 1;
  FUN_00105780();
  return;
}

