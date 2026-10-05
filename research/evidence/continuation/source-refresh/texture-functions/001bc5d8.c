
void FUN_001bc5d8(char *param_1,long param_2,char param_3)

{
  char cVar1;
  int iVar2;
  float fVar3;
  float fVar4;
  undefined1 in_zero_qw [16];
  undefined1 uVar5;
  undefined *puVar6;
  int iVar7;
  undefined8 uVar8;
  undefined4 *puVar9;
  undefined8 in_v1_udw;
  undefined1 (*pauVar10) [16];
  undefined1 in_a1_qw [16];
  undefined8 uVar11;
  long lVar12;
  long lVar13;
  undefined1 auVar14 [16];
  undefined1 auVar15 [16];
  undefined1 auVar16 [16];
  undefined1 auVar17 [16];
  undefined1 auVar18 [16];
  undefined1 auVar19 [16];
  undefined1 (*pauVar20) [16];
  int iVar21;
  char *pcVar22;
  int iVar23;
  char *pcVar24;
  int iVar25;
  undefined4 uVar26;
  undefined4 uVar27;
  undefined4 uVar28;
  int iVar29;
  undefined4 *puVar30;
  undefined4 uVar31;
  undefined1 in_vf0 [16];
  undefined1 auVar32 [16];
  undefined1 auVar33 [16];
  undefined1 auVar34 [16];
  undefined1 auVar35 [16];
  undefined1 auVar36 [16];
  undefined1 auStack_d0 [16];
  undefined1 auStack_c0 [16];
  undefined1 auStack_b0 [16];
  undefined4 auStack_90 [4];
  undefined1 auStack_80 [16];
  
  if (*param_1 < '\0') {
    puVar30 = (undefined4 *)0x0;
    pcRam00000000 = param_1;
  }
  else {
    puVar30 = (undefined4 *)(&DAT_00241b40 + *param_1 * 0x150);
    *puVar30 = param_1;
  }
  *(int *)(param_1 + 8) = in_a1_qw._0_4_;
  param_1[3] = param_3;
  if (in_a1_qw._0_8_ == 0) {
    uVar31 = 0;
    uVar26 = 0;
    uVar27 = 0;
    uVar28 = 0;
    FUN_00115498(auStack_d0);
  }
  else {
    iVar21 = *(int *)(in_a1_qw._0_4_ + 4);
    *(char **)(iVar21 + 0x84) = param_1;
    in_a1_qw._0_8_ = (long)(iVar21 + 0x20);
    uVar31 = *(undefined4 *)(iVar21 + 0x50);
    uVar26 = *(undefined4 *)(iVar21 + 0x54);
    uVar27 = *(undefined4 *)(iVar21 + 0x58);
    uVar28 = *(undefined4 *)(iVar21 + 0x5c);
    FUN_00114098(auStack_d0,in_a1_qw._0_8_);
  }
  pauVar20 = (undefined1 (*) [16])(param_1 + 0x50);
  pcVar22 = param_1 + 0x600;
  iVar21 = 4;
  auVar35 = _lqc2(auStack_d0);
  pcVar24 = param_1 + 0x170;
  do {
    auVar34 = _lqc2(auStack_c0);
    iVar21 = iVar21 + -1;
    auVar32 = _lqc2(auStack_b0);
    *(undefined4 *)pcVar22 = uVar31;
    *(undefined4 *)(pcVar22 + 4) = uVar26;
    *(undefined4 *)(pcVar22 + 8) = uVar27;
    *(undefined4 *)(pcVar22 + 0xc) = uVar28;
    pcVar22 = pcVar22 + 0x10;
    auVar33 = _sqc2(auVar35);
    pauVar20[-2] = auVar33;
    auVar36 = _vsub(auVar35,auVar35);
    auVar35 = _sqc2(auVar34);
    pauVar20[-1] = auVar35;
    auVar34 = _vsub(auVar34,auVar34);
    auVar35 = _sqc2(auVar32);
    *pauVar20 = auVar35;
    auVar33 = _vsub(auVar32,auVar32);
    auVar35 = _sqc2(auVar36);
    pauVar20[-2] = auVar35;
    auVar35 = _sqc2(auVar34);
    pauVar20[-1] = auVar35;
    auVar35 = _sqc2(auVar33);
    *pauVar20 = auVar35;
    pauVar20 = pauVar20 + 4;
    FUN_00114080(pcVar24);
    auVar35 = _lqc2(auStack_d0);
    pcVar24 = pcVar24 + 0x40;
  } while (-1 < iVar21);
  if (param_2 == -1) {
    cVar1 = param_1[1];
  }
  else {
    puVar9 = (undefined4 *)FUN_00125518();
    *(undefined4 *)(param_1 + 0x6f4) = *puVar9;
    *(undefined4 *)(param_1 + 0x6f8) = puVar9[2];
    *(undefined4 *)(param_1 + 0x6fc) = puVar9[4];
    *(undefined4 *)(param_1 + 0x700) = puVar9[1];
    *(undefined4 *)(param_1 + 0x704) = puVar9[3];
    *(undefined4 *)(param_1 + 0x708) = puVar9[5];
    cVar1 = param_1[1];
  }
  uVar11 = in_a1_qw._8_8_;
  switch(cVar1) {
  case '\x01':
    uVar8 = FUN_001946b8();
    break;
  case '\x02':
    uVar8 = FUN_001946b0();
    break;
  case '\x03':
    uVar8 = FUN_001946c0();
    in_a1_qw._0_8_ = 0x240000;
    break;
  case '\x04':
    uVar8 = FUN_001946c8();
    break;
  case '\x05':
    goto switchD_001bc758_caseD_5;
  default:
    goto switchD_001bc758_default;
  }
  uVar31 = FUN_001d60f0(uVar8);
  uVar11 = in_a1_qw._8_8_;
  *(undefined4 *)(&DAT_00241c1c + *param_1 * 0x150) = uVar31;
  uVar31 = FUN_001d6120(uVar8);
  *(undefined4 *)(&DAT_00241c20 + *param_1 * 0x150) = uVar31;
switchD_001bc758_caseD_5:
switchD_001bc758_default:
  FUN_001bf360();
  fVar4 = FLOAT_002901e8;
  fVar3 = FLOAT_002901e4;
  auVar35._0_8_ = (long)param_1[1];
  auVar35._8_8_ = in_v1_udw;
  if (auVar35._0_8_ == 4) {
    iVar21 = 0;
    if (param_1[0x470] == '\0') {
      iVar25 = *(int *)(param_1 + 0x6f0);
      iVar21 = *(int *)(param_1 + 0x708);
    }
    else {
      iVar25 = *(int *)(param_1 + 0x6f0);
      auVar35._0_8_ = (long)iVar25;
      do {
        puVar9 = auVar35._0_4_;
        puVar9[0x1c] = 0x3f000000;
        iVar21 = iVar21 + 1;
        puVar9[0x1d] = 0.29999998;
        *puVar9 = 3;
        auVar35._0_8_ = (long)(int)(puVar9 + 0x4c);
      } while (iVar21 < (int)(uint)(byte)param_1[0x470]);
      iVar21 = *(int *)(param_1 + 0x708);
    }
    auVar33._8_8_ = auVar35._8_8_;
    auVar32 = _pextlw((long)*(int *)(param_1 + 0x6f8),0);
    auVar34 = _pextlw(0,(long)iVar21);
    auVar35 = _pextlw(0,0);
    auVar32 = _por(in_zero_qw,auVar32);
    auVar18 = _pcpyld(auVar35,auVar32);
    auVar17 = _pextlw(0,(long)*(int *)(param_1 + 0x6f4));
    auVar16 = _pextlw(0,(long)*(int *)(param_1 + 0x700));
    auVar15 = _pextlw((long)*(int *)(param_1 + 0x704),0);
    auVar32 = _pextlw(0,(long)*(int *)(param_1 + 0x6fc));
    auVar36 = _por(in_zero_qw,auVar35);
    auVar14 = _pcpyld(auVar34,auVar36);
    auVar36 = _por(in_zero_qw,auVar18);
    auVar33._0_8_ = (long)(iVar25 + 0x860);
    auVar34 = _por(in_zero_qw,auVar35);
    auVar32 = _pcpyld(auVar32,auVar34);
    auVar19 = _por(in_zero_qw,auVar36);
    auVar17 = _pcpyld(auVar35,auVar17);
    auVar34 = _pcpyld(auVar35,auVar16);
    auVar35 = _pcpyld(auVar35,auVar15);
    iVar21 = 4;
    do {
      iVar21 = iVar21 + -1;
      puVar9 = auVar33._0_4_;
      puVar9[-0x214] = auVar18._0_4_;
      puVar9[-0x213] = auVar18._4_4_;
      puVar9[-0x212] = auVar18._8_4_;
      puVar9[-0x211] = auVar18._12_4_;
      puVar9[-0x1c8] = auVar19._0_4_;
      puVar9[-0x1c7] = auVar19._4_4_;
      puVar9[-0x1c6] = auVar19._8_4_;
      puVar9[-0x1c5] = auVar19._12_4_;
      puVar9[-0x17c] = auVar36._0_4_;
      puVar9[-0x17b] = auVar36._4_4_;
      puVar9[-0x17a] = auVar36._8_4_;
      puVar9[-0x179] = auVar36._12_4_;
      puVar9[-0x130] = auVar32._0_4_;
      puVar9[-0x12f] = auVar32._4_4_;
      puVar9[-0x12e] = auVar32._8_4_;
      puVar9[-0x12d] = auVar32._12_4_;
      puVar9[-0xe4] = auVar14._0_4_;
      puVar9[-0xe3] = auVar14._4_4_;
      puVar9[-0xe2] = auVar14._8_4_;
      puVar9[-0xe1] = auVar14._12_4_;
      puVar9[-0x98] = auVar17._0_4_;
      puVar9[-0x97] = auVar17._4_4_;
      puVar9[-0x96] = auVar17._8_4_;
      puVar9[-0x95] = auVar17._12_4_;
      puVar9[-0x4c] = auVar34._0_4_;
      puVar9[-0x4b] = auVar34._4_4_;
      puVar9[-0x4a] = auVar34._8_4_;
      puVar9[-0x49] = auVar34._12_4_;
      *puVar9 = auVar35._0_4_;
      puVar9[1] = auVar35._4_4_;
      puVar9[2] = auVar35._8_4_;
      puVar9[3] = auVar35._12_4_;
      auVar33._0_8_ = (long)(int)(puVar9 + 4);
    } while (-1 < iVar21);
  }
  else {
    if ((4 < auVar35._0_8_) || (auVar35._0_8_ < 1)) {
      *(float *)(param_1 + 0x710) = FLOAT_002901e0;
      *(float *)(param_1 + 0x714) = fVar3;
      *(float *)(param_1 + 0x718) = fVar4;
      goto LAB_001bca94;
    }
    iVar21 = *(int *)(param_1 + 0x6f0);
    for (iVar25 = 0; iVar25 < (int)(uint)(byte)param_1[0x470]; iVar25 = iVar25 + 1) {
      puVar9 = (undefined4 *)(iVar25 * 0x130 + iVar21);
      puVar9[0x1c] = 0.01;
      puVar9[0x1d] = 0.099999994;
      if (param_1[1] == '\x01') {
        puVar9[0x1c] = 0.29999998;
        puVar9[0x1d] = 0.02;
        *puVar9 = 1;
      }
      else {
        *puVar9 = 1;
      }
    }
    lVar12 = (long)*(int *)(param_1 + 0x700);
    auVar34._0_8_ = (long)(iVar21 + 0x860);
    auVar34._8_8_ = uVar11;
    auVar33 = _pextlw(0,(long)*(int *)(param_1 + 0x708));
    iVar21 = 4;
    lVar13 = (long)*(int *)(param_1 + 0x6f8);
    auVar36 = _pextlw(lVar13,(long)*(int *)(param_1 + 0x6f4));
    auVar17 = _pextlw((long)*(int *)(param_1 + 0x704),(long)*(int *)(param_1 + 0x6f4));
    auVar16 = _pextlw((long)*(int *)(param_1 + 0x704),lVar12);
    auVar35 = _pextlw(0,(long)*(int *)(param_1 + 0x6fc));
    auVar15 = _pextlw(lVar13,lVar12);
    auVar32 = _pextlw(lVar13,lVar12);
    auVar14 = _pcpyld(auVar35,auVar32);
    auVar18 = _por(in_zero_qw,auVar36);
    auVar19 = _pcpyld(auVar33,auVar36);
    auVar32 = _por(in_zero_qw,auVar16);
    auVar36 = _pcpyld(auVar33,auVar32);
    auVar32 = _por(in_zero_qw,auVar17);
    auVar32 = _pcpyld(auVar35,auVar32);
    auVar15 = _pcpyld(auVar33,auVar15);
    auVar18 = _pcpyld(auVar35,auVar18);
    auVar33 = _pcpyld(auVar33,auVar17);
    auVar35 = _pcpyld(auVar35,auVar16);
    do {
      iVar21 = iVar21 + -1;
      puVar9 = auVar34._0_4_;
      puVar9[-0x214] = auVar19._0_4_;
      puVar9[-0x213] = auVar19._4_4_;
      puVar9[-0x212] = auVar19._8_4_;
      puVar9[-0x211] = auVar19._12_4_;
      puVar9[-0x1c8] = auVar15._0_4_;
      puVar9[-0x1c7] = auVar15._4_4_;
      puVar9[-0x1c6] = auVar15._8_4_;
      puVar9[-0x1c5] = auVar15._12_4_;
      puVar9[-0x17c] = auVar18._0_4_;
      puVar9[-0x17b] = auVar18._4_4_;
      puVar9[-0x17a] = auVar18._8_4_;
      puVar9[-0x179] = auVar18._12_4_;
      puVar9[-0x130] = auVar14._0_4_;
      puVar9[-0x12f] = auVar14._4_4_;
      puVar9[-0x12e] = auVar14._8_4_;
      puVar9[-0x12d] = auVar14._12_4_;
      puVar9[-0xe4] = auVar33._0_4_;
      puVar9[-0xe3] = auVar33._4_4_;
      puVar9[-0xe2] = auVar33._8_4_;
      puVar9[-0xe1] = auVar33._12_4_;
      puVar9[-0x98] = auVar36._0_4_;
      puVar9[-0x97] = auVar36._4_4_;
      puVar9[-0x96] = auVar36._8_4_;
      puVar9[-0x95] = auVar36._12_4_;
      puVar9[-0x4c] = auVar32._0_4_;
      puVar9[-0x4b] = auVar32._4_4_;
      puVar9[-0x4a] = auVar32._8_4_;
      puVar9[-0x49] = auVar32._12_4_;
      *puVar9 = auVar35._0_4_;
      puVar9[1] = auVar35._4_4_;
      puVar9[2] = auVar35._8_4_;
      puVar9[3] = auVar35._12_4_;
      auVar34._0_8_ = (long)(int)(puVar9 + 4);
    } while (-1 < iVar21);
  }
  *(float *)(param_1 + 0x718) = 0.14999999;
  *(float *)(param_1 + 0x710) = 0.14999999;
  *(float *)(param_1 + 0x714) = 0.14999999;
LAB_001bca94:
  puVar6 = (undefined *)((int)puVar30 + 0x12d);
  iVar21 = 5;
  do {
    iVar21 = iVar21 + -1;
    *puVar6 = 1;
    puVar6 = puVar6 + 1;
  } while (-1 < iVar21);
  iVar21 = 0x3f800000;
  puVar30[0x51] = 0x40400000;
  param_1[0x4a0] = '\0';
  param_1[0x4a1] = '\0';
  param_1[0x4a2] = '\0';
  param_1[0x4a3] = '\0';
  param_1[0x4a4] = '\0';
  param_1[0x4a5] = '\0';
  param_1[0x4a6] = '\0';
  param_1[0x4a7] = '\0';
  param_1[0x4a8] = '\0';
  param_1[0x4a9] = '\0';
  param_1[0x4aa] = '\0';
  param_1[0x4ab] = '\0';
  param_1[0x4ac] = '\0';
  param_1[0x4ad] = '\0';
  param_1[0x4ae] = '\0';
  param_1[0x4af] = '\0';
  puVar30[0x52] = 0x3f800000;
  param_1[0x472] = 'P';
  iVar25 = 0;
  param_1[0x471] = '\0';
  param_1[0x473] = '\0';
  FUN_0020c7fc(param_1 + 0x4b0,0,0x50);
  FUN_0020c7fc(param_1 + 0x500,0,0x50);
  FUN_0020c7fc(param_1 + 0x650,0,0x50);
  FUN_0020c7fc(param_1 + 0x6a0,0,0x50);
  FUN_0020c7fc(param_1 + 0x550,0,0x50);
  FUN_0020c7fc(param_1 + 0x5a0,0,0x50);
  if (param_1[0x470] != '\0') {
    pauVar20 = (undefined1 (*) [16])(param_1 + 0x30);
    auVar35 = _pextlw(0,(long)iVar21);
    auVar33 = _pextlw(0,0);
    auVar35 = _pcpyld(auVar35,auVar33);
    iVar21 = *(int *)(param_1 + 0x6f0);
    iVar29 = 0;
    iVar23 = 0;
    do {
      iVar21 = iVar23 + iVar21;
      auVar36 = _lqc2(*pauVar20);
      iVar2 = *(int *)(iVar21 + 0x120);
      auVar32 = _lqc2(*(undefined1 (*) [16])(iVar21 + 0x10));
      _vmove(auVar32);
      auVar34 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x40));
      auVar33 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x50));
      _vmulabc(auVar36,auVar32);
      _vmaddabc(auVar34,auVar32);
      auVar33 = _vmaddbc(auVar33,auVar32);
      auVar33 = _sqc2(auVar33);
      *(undefined1 (*) [16])(iVar21 + 0x60) = auVar33;
      if (iVar2 != 0) {
        auVar32 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0x50));
        _vmove(auVar32);
        auVar36 = _lqc2(*pauVar20);
        auVar34 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x40));
        auVar33 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x50));
        _vmulabc(auVar36,auVar32);
        _vmaddabc(auVar34,auVar32);
        auVar33 = _vmaddbc(auVar33,auVar32);
        auVar33 = _sqc2(auVar33);
        *(undefined1 (*) [16])(iVar2 + 0x60) = auVar33;
      }
      auVar33 = _lqc2(*(undefined1 (*) [16])(iVar21 + 0x60));
      auVar32 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x600));
      auVar34 = _vadd(auVar32,auVar33);
      auVar33 = _qmfc2(auVar34._0_4_);
      auVar32 = _qmfc2(auVar34._0_4_);
      auVar33 = _pextuw(in_zero_qw,auVar33);
      auStack_80 = _sqc2(auVar34);
      FUN_00133ca0(auVar32._0_4_,auVar33._0_4_,auStack_90,iVar21 + 0x90,
                   *(undefined4 *)(iVar21 + 0x114));
      iVar21 = iVar23 + *(int *)(param_1 + 0x6f0);
      _lqc2(auStack_80);
      auVar33 = _qmtc2(auStack_90[0]);
      auVar32 = _lqc2(*(undefined1 (*) [16])(iVar21 + 0x90));
      auVar34 = _vsub(auVar32,auVar32);
      auVar32 = _vaddbc(in_vf0,auVar33);
      auVar33 = _sqc2(auVar34);
      *(undefined1 (*) [16])(iVar21 + 0xd0) = auVar33;
      auVar33 = _sqc2(auVar32);
      *(undefined1 (*) [16])(iVar21 + 0xc0) = auVar33;
      auVar33 = _sqc2(auVar32);
      *(undefined1 (*) [16])(iVar21 + 0xb0) = auVar33;
      auVar33 = _sqc2(auVar34);
      *(undefined1 (*) [16])(iVar21 + 0x90) = auVar33;
      auVar33 = _sqc2(auVar32);
      *(undefined1 (*) [16])(iVar21 + 0xe0) = auVar33;
      auVar33 = _sqc2(auVar34);
      *(undefined1 (*) [16])(iVar21 + 0xf0) = auVar33;
      uVar31 = *(undefined4 *)(param_1 + 0x54);
      uVar26 = *(undefined4 *)(param_1 + 0x58);
      uVar27 = *(undefined4 *)(param_1 + 0x5c);
      *(undefined4 *)(iVar21 + 0xa0) = *(undefined4 *)(param_1 + 0x50);
      *(undefined4 *)(iVar21 + 0xa4) = uVar31;
      *(undefined4 *)(iVar21 + 0xa8) = uVar26;
      *(undefined4 *)(iVar21 + 0xac) = uVar27;
      uVar5 = FUN_00134970(*(undefined4 *)(iVar21 + 0x114));
      *(undefined1 *)(iVar23 + *(int *)(param_1 + 0x6f0) + 7) = uVar5;
      uVar5 = FUN_001c3590(*(undefined1 *)(iVar23 + *(int *)(param_1 + 0x6f0) + 7));
      *(undefined1 *)(iVar23 + *(int *)(param_1 + 0x6f0) + 6) = uVar5;
      *(undefined1 *)(iVar23 + *(int *)(param_1 + 0x6f0) + 9) = 0;
      *(undefined1 *)(iVar23 + *(int *)(param_1 + 0x6f0) + 0x80) = 0;
      iVar21 = *(int *)(param_1 + 0x6f0);
      iVar7 = iVar23 + iVar21;
      iVar2 = *(int *)(iVar7 + 0x120);
      *(undefined4 *)(iVar7 + 0x104) = 0;
      *(undefined4 *)(iVar7 + 0x108) = 0;
      *(undefined4 *)(iVar7 + 0x10c) = 0;
      *(undefined4 *)(iVar7 + 0x110) = 0;
      if (iVar2 != 0) {
        *(int *)(iVar2 + 0x70) = auVar35._0_4_;
        *(int *)(iVar2 + 0x74) = auVar35._4_4_;
        *(int *)(iVar2 + 0x78) = auVar35._8_4_;
        *(int *)(iVar2 + 0x7c) = auVar35._12_4_;
        iVar7 = 4;
        auVar33 = _prot3w(*pauVar20);
        auVar32 = _prot3w(*(undefined1 (*) [16])(param_1 + 0x40));
        uVar31 = FUN_00204ed0(-auVar33._0_4_,auVar32._0_4_);
        auVar36 = _lqc2(*pauVar20);
        auVar34 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x40));
        iVar21 = *(int *)(iVar23 + *(int *)(param_1 + 0x6f0) + 0x120);
        auVar32 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x50));
        auVar33 = _lqc2(*(undefined1 (*) [16])(iVar21 + 0x70));
        _vmove(auVar33);
        _vmulabc(auVar36,auVar33);
        _vmaddabc(auVar34,auVar33);
        auVar33 = _vmaddbc(auVar32,auVar33);
        auVar33 = _qmfc2(auVar33._0_4_);
        FUN_00115830(uVar31,iVar21 + 0x10,auVar33._0_8_);
        iVar21 = *(int *)(param_1 + 0x6f0);
        auVar36 = _lqc2(*pauVar20);
        iVar2 = *(int *)(iVar23 + iVar21 + 0x120);
        pauVar10 = (undefined1 (*) [16])(iVar29 * 0x10 + iVar21);
        auVar34 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x40));
        auVar33 = _lqc2(*(undefined1 (*) [16])(iVar2 + 0xb0));
        _vmove(auVar33);
        auVar32 = _lqc2(*(undefined1 (*) [16])(param_1 + 0x50));
        _vmulabc(auVar36,auVar33);
        _vmaddabc(auVar34,auVar33);
        auVar33 = _vmaddbc(auVar32,auVar33);
        *(undefined4 *)(iVar2 + 0xd0) = 0;
        puVar30 = (undefined4 *)(iVar2 + 0x16c);
        *(undefined4 *)(iVar2 + 0x80) = 0;
        *(undefined4 *)(iVar2 + 0x84) = 0;
        *(undefined4 *)(iVar2 + 0x88) = 0;
        *(undefined4 *)(iVar2 + 0x8c) = 0;
        *(undefined4 *)(iVar2 + 0xd4) = 0;
        *(undefined4 *)(iVar2 + 0xa0) = 0;
        *(undefined4 *)(iVar2 + 0xa4) = 0;
        *(undefined4 *)(iVar2 + 0xa8) = 0;
        *(undefined4 *)(iVar2 + 0xac) = 0;
        *(undefined4 *)(iVar2 + 0xe8) = 0;
        *(undefined4 *)(iVar2 + 0x90) = 0;
        *(undefined4 *)(iVar2 + 0x94) = 0;
        *(undefined4 *)(iVar2 + 0x98) = 0;
        *(undefined4 *)(iVar2 + 0x9c) = 0;
        *(undefined4 *)(iVar2 + 0xe0) = 0;
        *(undefined4 *)(iVar2 + 0xf0) = 0;
        *(undefined4 *)(iVar2 + 0xf4) = 0;
        *(undefined4 *)(iVar2 + 0xd8) = 0;
        *(undefined4 *)(iVar2 + 0xdc) = 0;
        *(undefined4 *)(iVar2 + 0xec) = 0;
        *(undefined4 *)(iVar2 + 0xf8) = 0;
        *(undefined4 *)(iVar2 + 0x104) = 0;
        *(undefined4 *)(iVar2 + 0xfc) = 0;
        *(undefined4 *)(iVar2 + 0x100) = 0;
        *(undefined4 *)(iVar2 + 0x10c) = 0;
        *(undefined4 *)(iVar2 + 0x110) = 0;
        *(undefined4 *)(iVar2 + 0x114) = 0;
        *(undefined4 *)(iVar2 + 0x118) = 0;
        auVar33 = _sqc2(auVar33);
        *(undefined1 (*) [16])(iVar2 + 0xc0) = auVar33;
        auVar33 = _qmtc2(0);
        do {
          pauVar10 = pauVar10 + 1;
          _lqc2(*pauVar10);
          auVar32 = _vaddbc(in_vf0,auVar33);
          iVar7 = iVar7 + -1;
          auVar32 = _sqc2(auVar32);
          *pauVar10 = auVar32;
          puVar30[-0x14] = 0;
          puVar30[-0xf] = 0;
          puVar30[-10] = 0;
          puVar30[-5] = 0;
          *puVar30 = 0;
          puVar30 = puVar30 + 1;
        } while (-1 < iVar7);
      }
      iVar25 = iVar25 + 1;
      iVar29 = iVar29 + 0x13;
      iVar23 = iVar23 + 0x130;
    } while (iVar25 < (int)(uint)(byte)param_1[0x470]);
  }
  return;
}

