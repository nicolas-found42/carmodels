
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

float * FUN_0021bc18(int param_1,ushort *param_2)

{
  ushort uVar1;
  uint uVar2;
  uint uVar3;
  undefined1 in_zero_qw [16];
  undefined1 auVar4 [16];
  long lVar5;
  float *pfVar6;
  float fVar7;
  float fVar8;
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  
  uVar1 = *param_2;
  pfVar6 = (float *)(param_2 + 4);
  if ((uVar1 & 0x100) != 0) {
    fRam0028f1e0 = *pfVar6;
    pfVar6 = (float *)(param_2 + 6);
  }
  lVar5 = -0x7f7f7f80;
  if ((param_2[2] == 0xffff) || ((uVar1 & 6) != 0)) {
    lVar5 = (long)(int)*pfVar6;
    pfVar6 = pfVar6 + 1;
  }
  auVar4 = _pextlb(0,lVar5);
  auVar4 = _pextlh(0,auVar4._0_8_);
  auVar4 = _pexew(auVar4);
  auVar4 = _qmtc2(auVar4._0_4_);
  if ((uVar1 & 1) == 0) {
    auVar4 = _vitof0(auVar4);
    auVar9 = _qmtc2(DAT_70003560 * FLOAT_0028f1e8);
    auVar4 = _vmulbc(auVar4,auVar9);
  }
  else {
    auVar4 = _vitof0(auVar4);
    lVar5 = (long)(int)FLOAT_0028f178;
    auVar9 = _qmtc2(FLOAT_0028f178);
    auVar4 = _vmulbc(auVar4,auVar9);
  }
  fVar7 = (float)lVar5;
  _DAT_70003520 = _sqc2(auVar4);
  if ((uVar1 & 8) != 0) {
    fVar8 = *pfVar6;
    pfVar6 = pfVar6 + 1;
    fVar7 = DAT_70003560 * 1.4285713;
    auVar4 = _pextlb(0,(long)(int)fVar8);
    auVar4 = _pextlh(0,auVar4._0_8_);
    auVar4 = _pexew(auVar4);
    auVar4 = _qmtc2(auVar4._0_4_);
    auVar9 = _vitof0(auVar4);
    auVar10 = _qmtc2(0.01);
    auVar4 = _qmtc2(fVar7);
    auVar9 = _vmulbc(auVar9,auVar10);
    auVar4 = _vmulbc(auVar9,auVar4);
    _DAT_70003530 = _sqc2(auVar4);
  }
  if ((uVar1 & 0x10) != 0) {
    auVar4._4_4_ = DAT_700034d4;
    auVar4._0_4_ = DAT_700034d0;
    auVar4._8_4_ = DAT_700034d8;
    auVar4._12_4_ = DAT_700034dc;
    auVar4 = _pextuw(in_zero_qw,auVar4);
    auVar4 = _pexew(auVar4);
    fVar8 = 1.0;
    fVar7 = *pfVar6;
    pfVar6 = pfVar6 + 1;
    if (auVar4._0_4_ <= 1.0) {
      fVar8 = DAT_70003560 * auVar4._0_4_;
    }
    auVar4 = _pextlb(0,(long)(int)fVar7);
    auVar4 = _pextlh(0,auVar4._0_8_);
    auVar4 = _pexew(auVar4);
    auVar4 = _qmtc2(auVar4._0_4_);
    auVar4 = _vitof0(auVar4);
    auVar9 = _qmtc2(fVar8);
    auVar4 = _vmulbc(auVar4,auVar9);
    _DAT_70003540 = _sqc2(auVar4);
  }
  if ((uVar1 & 0x80) != 0) {
    uVar2 = (int)pfVar6 + 3U & 3;
    uVar3 = (uint)pfVar6 & 3;
    fVar7 = (float)((*(int *)(((int)pfVar6 + 3U) - uVar2) << (3 - uVar2) * 8 |
                    (uint)fVar7 & 0xffffffffU >> (uVar2 + 1) * 8) & -1 << (4 - uVar3) * 8 |
                   *(uint *)((int)pfVar6 - uVar3) >> uVar3 * 8);
    pfVar6 = pfVar6 + 1;
    uVar1 = *param_2;
    DAT_70003000 = fVar7;
  }
  if ((uVar1 & 0x40) != 0) {
    uVar2 = (int)pfVar6 + 3U & 3;
    uVar3 = (uint)pfVar6 & 3;
    DAT_70003010 = (*(int *)(((int)pfVar6 + 3U) - uVar2) << (3 - uVar2) * 8 |
                   (uint)fVar7 & 0xffffffffU >> (uVar2 + 1) * 8) & -1 << (4 - uVar3) * 8 |
                   *(uint *)((int)pfVar6 - uVar3) >> uVar3 * 8;
    pfVar6 = pfVar6 + 1;
  }
  uRam0028f17c = 0;
  if (param_2[2] != 0xffff) {
    uRam0028f17c = *(undefined4 *)((uint)param_2[2] * 4 + *(int *)(param_1 + 0xec));
  }
  return pfVar6;
}

