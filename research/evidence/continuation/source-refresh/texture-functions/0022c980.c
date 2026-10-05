
void FUN_0022c980(void)

{
  int iVar1;
  int iVar2;
  
  FUN_00202a70();
  iVar2 = 0;
  iVar1 = 0;
  do {
    *(int *)(iVar1 + 0x290630) = iVar2;
    iVar2 = iVar2 + 1;
    *(undefined4 *)(iVar1 + 0x290638) = 0;
    *(undefined4 *)(iVar1 + 0x290640) = 0;
    *(undefined4 *)(iVar1 + 0x290648) = 0xffffffff;
    *(undefined4 *)(iVar1 + 0x290650) = 0xffffffff;
    *(undefined4 *)(iVar1 + 0x290658) = 0xffffffff;
    iVar1 = iVar1 + 4;
  } while (iVar2 < 2);
  return;
}

