
void FUN_001217f8(undefined4 param_1,undefined4 *param_2,int param_3,int param_4)

{
  uint uVar1;
  undefined4 uVar2;
  int iVar3;
  undefined1 auVar4 [16];
  undefined1 auVar5 [16];
  undefined4 *puVar6;
  int iVar7;
  
  if (0 < param_4) {
    do {
      iVar3 = iGpffff93c8;
      uVar1 = *(uint *)(param_3 + 4);
      puVar6 = param_2 + 4;
      *param_2 = param_1;
      if ((uVar1 & 0x10000) != 0) {
        param_2[8] = *(undefined4 *)(param_3 + 0x18);
        puVar6 = param_2 + 0x10;
        param_2[9] = *(undefined4 *)(param_3 + 0x1c);
        param_2[10] = *(undefined4 *)(param_3 + 0x20);
        iVar7 = *(int *)(param_3 + 0x14);
        auVar4 = _pextlw((long)*(int *)(param_3 + 0x10),(long)*(int *)(param_3 + 0xc));
        param_2[0xb] = 0x3f800000;
        auVar5 = _pextlw(0x3f800000,(long)iVar7);
        auVar4 = _pcpyld(auVar5,auVar4);
        uVar1 = *(uint *)(param_3 + 4);
        param_2[4] = auVar4._0_4_;
        param_2[5] = auVar4._4_4_;
        param_2[6] = auVar4._8_4_;
        param_2[7] = auVar4._12_4_;
        *(ulong *)(param_2 + 2) =
             *(ulong *)(param_2 + 2) & 0xffffffffffffffee | (long)(int)(uVar1 >> 0xe) & 1U;
      }
      if (*(char *)(param_3 + 4) == '\0') {
        param_2[1] = 0;
      }
      else {
        uVar1 = *(uint *)(param_3 + 4);
        uVar2 = *(undefined4 *)(param_3 + 0x28);
        param_2[1] = iGpffff93c8;
        iGpffff93c8 = iGpffff93c8 + (uVar1 >> 8 & 0x3f) * 0x30 + (uint)*(byte *)(param_3 + 4) * 0x10
        ;
        FUN_001217f8(param_2,iVar3,uVar2);
      }
      param_4 = param_4 + -1;
      param_3 = param_3 + 0x2c;
      param_2 = puVar6;
    } while (param_4 != 0);
  }
  return;
}

