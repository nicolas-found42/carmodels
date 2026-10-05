
void FUN_0022c498(int param_1)

{
  int iVar1;
  
  FUN_00112168();
  if (*(int *)(param_1 + 0x10c) == 0) {
    iVar1 = *(int *)(param_1 + 0x108);
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0x10c) = 0;
    iVar1 = *(int *)(param_1 + 0x108);
  }
  if (iVar1 == 0) {
    iVar1 = *(int *)(param_1 + 0x104);
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0x108) = 0;
    iVar1 = *(int *)(param_1 + 0x104);
  }
  if (iVar1 == 0) {
    iVar1 = *(int *)(param_1 + 0xf4);
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0x104) = 0;
    iVar1 = *(int *)(param_1 + 0xf4);
  }
  if (iVar1 == 0) {
    iVar1 = *(int *)(param_1 + 0xec);
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0xf4) = 0;
    iVar1 = *(int *)(param_1 + 0xec);
  }
  if (iVar1 == 0) {
    iVar1 = *(int *)(param_1 + 0xf8);
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0xec) = 0;
    iVar1 = *(int *)(param_1 + 0xf8);
  }
  if (iVar1 == 0) {
    *(undefined4 *)(param_1 + 0xfc) = 0;
  }
  else {
    FUN_0010d100();
    *(undefined4 *)(param_1 + 0xf8) = 0;
    *(undefined4 *)(param_1 + 0xe0) = 0;
    *(undefined4 *)(param_1 + 0xfc) = 0;
  }
  return;
}

