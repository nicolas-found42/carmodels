
void FUN_00123820(int param_1,undefined4 param_2)

{
  int iVar1;
  int *piVar2;
  int *piVar3;
  int iVar4;
  int iVar5;
  
  iVar4 = 0;
  if (0 < iGpffffaa20) {
    iVar5 = 0;
    piVar2 = piGpffff93cc;
    piVar3 = piGpffff93cc;
    do {
      iVar1 = *piVar3;
      piVar3 = piVar3 + 3;
      if (iVar1 == param_1) {
        *(undefined4 *)(piVar2[1] * 4 + piVar2[2]) = param_2;
        *(int *)((int)piGpffff93cc + iVar5 + 4) = *(int *)((int)piGpffff93cc + iVar5 + 4) + 1;
        return;
      }
      iVar4 = iVar4 + 1;
      piVar2 = piVar2 + 3;
      iVar5 = iVar5 + 0xc;
    } while (iVar4 < iGpffffaa20);
  }
                    /* WARNING: Subroutine does not return */
  FUN_00105888(0x2528f8,0x2fd,0x2529e8);
}

