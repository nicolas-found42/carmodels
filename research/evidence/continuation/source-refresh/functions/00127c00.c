
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00127c00(long param_1)

{
  undefined1 auVar1 [16];
  undefined1 auVar2 [16];
  undefined1 auVar3 [16];
  float fVar4;
  float fVar5;
  float fVar6;
  float fVar7;
  undefined1 in_vf0 [16];
  undefined1 auVar8 [16];
  undefined1 auVar9 [16];
  undefined1 auVar10 [16];
  undefined1 auVar11 [16];
  undefined1 auStack_90 [16];
  undefined1 auStack_80 [16];
  undefined1 auStack_70 [16];
  undefined4 uStack_60;
  undefined4 uStack_5c;
  undefined4 uStack_58;
  undefined4 uStack_54;
  
  fVar4 = *(float *)(iRam0028f0ec + 0x3c) - *(float *)(iRam0028f0ec + 0x34);
  fVar5 = *(float *)(iRam0028f0ec + 0x40) - *(float *)(iRam0028f0ec + 0x38);
  fVar6 = (*(float *)(iRam0028f0ec + 0x34) - (float)(int)DAT_002324fc * 0.5) + 2048.0;
  fVar7 = (*(float *)(iRam0028f0ec + 0x38) - (float)(int)DAT_002324fe * 0.5) + 2048.0;
  if (param_1 == 0) {
    FUN_001154d0(0x700030e0);
  }
  else {
    FUN_00114098(0x700030e0,uRam0028f0f0);
    auVar8 = _lqc2(_DAT_700030e0);
    auVar9 = _lqc2(_DAT_700030f0);
    auVar10 = _vsub(auVar9,auVar9);
    auVar9 = _lqc2(_DAT_70003100);
    auVar9 = _vsub(auVar9,auVar9);
    auVar8 = _vsub(auVar8,auVar8);
    auVar11 = _vmove(in_vf0);
    _DAT_700030e0 = _sqc2(auVar8);
    _DAT_70003110 = _sqc2(auVar11);
    _DAT_700030f0 = _sqc2(auVar10);
    _DAT_70003100 = _sqc2(auVar9);
  }
  FUN_00115518(0x70003120,0x700030e0);
  if (param_1 == 0) {
    FUN_00114080(0x700031e0);
    FUN_00114080(0x70003220);
    FUN_00114080(0x70003160);
    FUN_00114080(auStack_90);
    _lqc2(_DAT_70003160);
    _lqc2(_DAT_70003170);
    _lqc2(_DAT_70003190);
    _lqc2(auStack_90);
    auVar9 = _vmove(in_vf0);
    _lqc2(auStack_80);
    _lqc2(auStack_70);
    _DAT_70003190 = _sqc2(auVar9);
    auVar8 = _pextlw((long)(int)(fVar5 * 0.5 + fVar7),(long)(int)(fVar4 * 0.5 + fVar6));
    auVar9 = _qmtc2(-2.0 / (float)(int)DAT_002324fc);
    auVar10 = _vaddbc(in_vf0,auVar9);
    auVar9 = _qmtc2(fVar4 * 0.5);
    auVar1 = _vaddbc(in_vf0,auVar9);
    _DAT_70003160 = _sqc2(auVar10);
    auVar10 = _qmtc2(fVar5 * -0.5);
    auVar9 = _qmtc2(-2.0 / (float)(int)DAT_002324fe);
    auVar9 = _vaddbc(in_vf0,auVar9);
    _DAT_70003170 = _sqc2(auVar9);
    auVar11 = _vaddbc(in_vf0,auVar10);
    auVar9 = _qmtc2(0xc7800000);
    auVar10 = _vaddbc(in_vf0,auVar9);
    auVar9 = _pextlw(0x3f800000,0x47800000);
    auVar9 = _pcpyld(auVar9,auVar8);
    auStack_90 = _sqc2(auVar1);
    auStack_80 = _sqc2(auVar11);
    auStack_70 = _sqc2(auVar10);
    uStack_60 = auVar9._0_4_;
    uStack_5c = auVar9._4_4_;
    uStack_58 = auVar9._8_4_;
    uStack_54 = auVar9._12_4_;
    FUN_00115560(0x70003160,0x70003160,auStack_90);
  }
  else {
    FUN_00128518(fVar4,fVar5,*(undefined4 *)(iRam0028f0ec + 8),*(undefined4 *)(iRam0028f0ec + 0xc),
                 fVar4 * 0.5 + fVar6,fVar5 * 0.5 + fVar7,0x3f800000,0x47800000,0x70003160,0x700031e0
                 ,0x70003220);
  }
  auVar2 = _pextlw(0x42800000,0x42fe0000);
  auVar1 = _pextlw(0x42800000,0x43000000);
  auVar3 = _pextlw(0x43000000,(long)(int)((float)bRam002907d0 * 0.5));
  auVar11 = _pextlw((long)(int)((float)bRam002907d1 * 0.5),(long)(int)((float)bRam002907d2 * 0.5));
  auVar10 = _pextlw(0x42fe0000,0x42fe0000);
  auVar9 = _pextlw(0x43000000,0x43000000);
  auVar9 = _pcpyld(auVar9,auVar9);
  auVar8 = _pextlw(0x43000000,0x43000000);
  auVar8 = _pcpyld(auVar1,auVar8);
  auVar10 = _pcpyld(auVar2,auVar10);
  auVar11 = _pcpyld(auVar3,auVar11);
  DAT_70003570 = auVar10._0_4_;
  DAT_70003574 = auVar10._4_4_;
  DAT_70003578 = auVar10._8_4_;
  DAT_7000357c = auVar10._12_4_;
  DAT_70003580 = auVar8._0_4_;
  DAT_70003584 = auVar8._4_4_;
  DAT_70003588 = auVar8._8_4_;
  DAT_7000358c = auVar8._12_4_;
  DAT_700035b0 = auVar9._0_4_;
  DAT_700035b4 = auVar9._4_4_;
  DAT_700035b8 = auVar9._8_4_;
  DAT_700035bc = auVar9._12_4_;
  DAT_700035c0 = auVar11._0_4_;
  DAT_700035c4 = auVar11._4_4_;
  DAT_700035c8 = auVar11._8_4_;
  DAT_700035cc = auVar11._12_4_;
  return;
}

