
uint FUN_00229d50(undefined4 *param_1,undefined8 *param_2,undefined1 (*param_3) [16])

{
  undefined1 in_zero_qw [16];
  uint uVar1;
  uint uVar2;
  uint uVar3;
  undefined1 auVar4 [16];
  undefined1 auVar5 [16];
  float fVar6;
  float fVar7;
  undefined1 in_vf0 [16];
  undefined1 auVar8 [16];
  undefined4 uVar9;
  undefined1 auVar10 [16];
  undefined1 auVar11 [16];
  undefined1 auVar12 [16];
  undefined1 auVar13 [16];
  undefined1 auVar14 [16];
  undefined4 uStack_60;
  undefined4 uStack_5c;
  undefined4 uStack_58;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined4 uStack_48;
  undefined4 uStack_44;
  undefined4 uStack_40;
  undefined4 uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  undefined1 auStack_30 [16];
  
  uStack_48 = *(undefined4 *)(param_2 + 3);
  uStack_44 = *(undefined4 *)((int)param_2 + 0x1c);
  uStack_40 = *(undefined4 *)(param_2 + 4);
  uStack_3c = *(undefined4 *)((int)param_2 + 0x24);
  uStack_38 = *(undefined4 *)(param_2 + 5);
  uStack_34 = *(undefined4 *)((int)param_2 + 0x2c);
  uStack_58 = *(undefined4 *)(param_2 + 1);
  uStack_54 = *(undefined4 *)((int)param_2 + 0xc);
  uStack_50 = (undefined4)param_2[2];
  uStack_4c = (undefined4)((ulong)param_2[2] >> 0x20);
  uStack_60 = (undefined4)*param_2;
  uStack_5c = (undefined4)((ulong)*param_2 >> 0x20);
  auStack_30 = ZEXT816(0);
  FUN_00115560(&uStack_60,&uStack_60,0x2341b0);
  auVar8 = _lqc2(*param_3);
  auVar10._4_4_ = uStack_5c;
  auVar10._0_4_ = uStack_60;
  auVar10._8_4_ = uStack_58;
  auVar10._12_4_ = uStack_54;
  auVar13 = _lqc2(auVar10);
  DAT_700035a0 = 0;
  auVar11._4_4_ = uStack_4c;
  auVar11._0_4_ = uStack_50;
  auVar11._8_4_ = uStack_48;
  auVar11._12_4_ = uStack_44;
  auVar12 = _lqc2(auVar11);
  uVar3 = 0x2aaaa;
  _vmove(auVar8);
  auVar10 = _vmove(in_vf0);
  _sqc2(auVar8);
  uVar2 = 7;
  _sqc2(auVar10);
  auVar14 = _vmove(in_vf0);
  auVar8._4_4_ = uStack_3c;
  auVar8._0_4_ = uStack_40;
  auVar8._8_4_ = uStack_38;
  auVar8._12_4_ = uStack_34;
  auVar11 = _lqc2(auVar8);
  auVar10 = _vmove(auVar10);
  do {
    _vmove(auVar14);
    if ((uVar2 & 1) == 0) {
      auVar8 = _qmtc2(*param_1);
    }
    else {
      auVar8 = _qmtc2(param_1[1]);
    }
    _vaddbc(in_vf0,auVar8);
    if ((uVar2 & 2) == 0) {
      auVar8 = _qmtc2(param_1[2]);
    }
    else {
      auVar8 = _qmtc2(param_1[3]);
    }
    _vaddbc(in_vf0,auVar8);
    if ((uVar2 & 4) == 0) {
      auVar8 = _qmtc2(param_1[4]);
    }
    else {
      auVar8 = _qmtc2(param_1[5]);
    }
    auVar8 = _vaddbc(in_vf0,auVar8);
    _vmulabc(auVar13,auVar8);
    _vmaddabc(auVar12,auVar8);
    _vmaddabc(auVar11,auVar8);
    auVar8 = _vmaddbc(auVar10,auVar8);
    uVar9 = auVar8._0_4_;
    auVar8 = _qmfc2(uVar9);
    auVar4 = _pextuw(in_zero_qw,auVar8);
    auVar8 = _qmfc2(uVar9);
    fVar7 = -auVar4._0_4_;
    fVar6 = auVar8._0_4_ * DAT_002341f0;
    uVar1 = 0;
    if (fVar6 < fVar7 * DAT_002341f8) {
      uVar1 = 0x2000;
    }
    if (-fVar6 < fVar7 * DAT_002341f8) {
      uVar1 = uVar1 | 0x8000;
    }
    auVar5 = _qmfc2(uVar9);
    auVar5 = _prot3w(auVar5);
    fVar6 = auVar5._0_4_ * DAT_00234214;
    if (fVar6 < fVar7 * DAT_00234218) {
      uVar1 = uVar1 | 0x20000;
    }
    if (-fVar6 < fVar7 * DAT_00234218) {
      uVar1 = uVar1 | 0x80;
    }
    if (auVar4._0_4_ * DAT_00234238 < DAT_0023423c) {
      uVar1 = uVar1 | 0x200;
    }
    fVar6 = auVar8._0_4_ * DAT_00234240;
    if (fVar6 < fVar7 * DAT_00234248) {
      uVar1 = uVar1 | 0x800;
    }
    if (-fVar6 < fVar7 * DAT_00234248) {
      uVar1 = uVar1 | 2;
    }
    fVar6 = auVar5._0_4_ * DAT_00234264;
    if (fVar6 < fVar7 * DAT_00234268) {
      uVar1 = uVar1 | 8;
    }
    if (-fVar6 < fVar7 * DAT_00234268) {
      uVar1 = uVar1 | 0x20;
    }
    uVar2 = uVar2 - 1;
    uVar3 = uVar3 & uVar1;
    DAT_700035a0 = DAT_700035a0 | uVar1;
  } while (-1 < (int)uVar2);
  return uVar3;
}

