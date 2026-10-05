
undefined4 FUN_00105660(int param_1)

{
  undefined4 uVar1;
  
  uVar1 = 0;
  if (*(int *)(param_1 + 0x104) != 0) {
    if (*(int *)(param_1 + 0x108) == 0) {
      uVar1 = 0;
    }
    else {
      FUN_00105780();
      uVar1 = 1;
    }
  }
  return uVar1;
}

