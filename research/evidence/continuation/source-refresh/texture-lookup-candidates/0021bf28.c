
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

uint FUN_0021bf28(uint param_1,int param_2,ushort *param_3,int param_4,int param_5)

{
  byte bVar1;
  ushort uVar2;
  ushort uVar3;
  int iVar4;
  uint uVar5;
  uint uVar6;
  uint uVar7;
  uint uVar8;
  uint uVar9;
  uint uVar10;
  undefined1 in_vf0 [16];
  undefined1 auVar11 [16];
  
  uVar2 = *param_3;
  param_1 = (uVar2 & 1) << 5 | param_1;
  if ((uVar2 & 4) != 0) {
    param_1 = param_1 | 1;
  }
  if ((uVar2 & 8) != 0) {
    param_1 = param_1 | 0x40;
  }
  if ((uVar2 & 0x10) != 0) {
    param_1 = param_1 | 0x80;
  }
  if ((uVar2 & 0x400) == 0) {
    param_1 = param_1 | 0x200;
  }
  uVar5 = param_1;
  if ((DAT_70003560 != 1.0) && (uVar5 = param_1 | 2, iRam0028f1d8 != 0)) {
    uRam0028f17c = 0;
    uVar5 = param_1 & 0xffffff3f | 2;
  }
  uVar3 = param_3[1];
  if (((uVar5 & 0x100) == 0) && ((uVar2 & 0x20) != 0)) {
    uVar5 = uVar5 | 0x10;
  }
  iVar4 = (uint)uVar3 * 4;
  uVar7 = (param_4 + (uint)uVar3 * 6 + 0xf & 0xfffffff0) + iVar4 + 0xf & 0xfffffff0;
  uVar6 = uVar7;
  uVar8 = 0;
  if (param_3[2] != 0xffff) {
    uVar6 = uVar7 + iVar4 + 0xf & 0xfffffff0;
    uVar8 = uVar7;
  }
  uVar7 = uVar6;
  uVar9 = 0;
  if ((uVar2 & 0x80) != 0) {
    uVar7 = uVar6 + iVar4 + 0xf & 0xfffffff0;
    uVar9 = uVar6;
  }
  uVar6 = uVar7;
  uVar10 = 0;
  if ((uVar2 & 0x40) != 0) {
    uVar6 = uVar7 + iVar4 + 0xf & 0xfffffff0;
    uVar10 = uVar7;
  }
  if (((uVar5 & 8) == 0) || ((uVar2 & 0x10) == 0)) {
    FUN_0021c3e0(uVar3);
  }
  else {
    FUN_00128218(uVar3);
  }
  if ((((uVar5 & 8) != 0) && ((*param_3 & 8) != 0)) && (iRam0028f1fc != 0)) {
    FUN_0021cc88(0x58,0xffffffffff000000,param_3[1],uVar8,_DAT_700035c0,uRam0028f184,uVar5);
  }
  if ((uVar9 != 0) && (iRam0028f204 != 0)) {
    FUN_0021cc88(0x80000000a1,0xffffffffff000000,param_3[1],uVar9,_DAT_700035b0,
                 *(undefined4 *)((uint)DAT_70003000._2_2_ * 4 + *(int *)(param_2 + 0xec)),uVar5);
  }
  if ((uVar10 != 0) && (iRam0028f204 != 0)) {
    FUN_0021cc88(0x44,0xffffffffff000000,param_3[1],uVar10,_DAT_70003580,
                 *(undefined4 *)((uint)DAT_70003010._2_2_ * 4 + *(int *)(param_2 + 0xec)),uVar5);
  }
  if ((param_5 != 0) && ((*param_3 & 0x200) != 0)) {
    bVar1 = *(byte *)(param_5 + 0xd3);
    while( true ) {
      _lqc2(_DAT_70003570);
      auVar11 = _qmtc2((float)(bVar1 >> 1));
      auVar11 = _vmulbc(in_vf0,auVar11);
      _DAT_70003570 = _sqc2(auVar11);
      _qmfc2(auVar11._0_4_);
      FUN_0021ced0(param_3[1]);
      param_5 = *(int *)(param_5 + 0xd4);
      if (param_5 == 0) break;
      bVar1 = *(byte *)(param_5 + 0xd3);
    }
  }
  FUN_0021d090();
  return uVar6;
}

