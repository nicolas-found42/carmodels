
/* source file (direct reference to its __FILE__ string, not proof of authorship):
   ../fr2/source/physics/physics.c:764 */

ulong FUN_001bbce0(long param_1,undefined4 param_2,ulong param_3,long param_4,int param_5,
                  undefined4 param_6,undefined4 param_7)

{
  int iVar1;
  undefined4 uVar2;
  undefined4 uVar3;
  undefined4 uVar4;
  float fVar5;
  undefined1 in_zero_qw [16];
  int iVar6;
  undefined4 *puVar7;
  undefined4 uVar8;
  int iVar9;
  int *piVar10;
  undefined8 uVar11;
  undefined8 uVar12;
  long lVar13;
  undefined1 auVar14 [16];
  long lVar15;
  undefined4 uVar16;
  undefined1 (*pauVar17) [16];
  undefined4 uVar19;
  undefined4 uVar20;
  undefined1 auVar18 [16];
  undefined4 uVar21;
  long lVar22;
  long lVar23;
  undefined1 auVar24 [16];
  undefined1 auVar25 [16];
  long lVar26;
  undefined1 auVar27 [16];
  undefined1 auVar28 [16];
  undefined1 auVar29 [16];
  undefined1 auVar30 [16];
  undefined1 auVar31 [16];
  undefined1 auVar32 [16];
  undefined1 auVar33 [16];
  undefined1 in_s0_qw [16];
  int iVar34;
  undefined1 in_s1_qw [16];
  int iVar35;
  int iVar36;
  undefined1 *puVar37;
  ulong uVar38;
  undefined1 auVar39 [16];
  float fVar40;
  int iVar41;
  int iVar42;
  undefined1 in_vf0 [16];
  undefined1 auVar43 [16];
  undefined1 auVar44 [16];
  undefined4 uStack_f0;
  int iStack_ec;
  undefined4 uStack_e8;
  undefined4 uStack_e4;
  undefined4 uStack_d0;
  int iStack_cc;
  undefined4 uStack_c8;
  undefined4 uStack_c4;
  undefined *puStack_c0;
  int iStack_bc;
  undefined4 uStack_b0;
  undefined4 uStack_ac;
  undefined4 uStack_a8;
  undefined4 uStack_a4;
  int iStack_a0;
  undefined4 uStack_90;
  undefined4 uStack_8c;
  undefined4 uStack_88;
  undefined4 uStack_84;
  undefined4 uStack_80;
  undefined4 uStack_7c;
  undefined4 uStack_78;
  undefined4 uStack_74;
  
  uStack_80 = in_s1_qw._0_4_;
  uStack_7c = in_s1_qw._4_4_;
  uStack_78 = in_s1_qw._8_4_;
  uStack_74 = in_s1_qw._12_4_;
  auVar43._8_8_ = in_s1_qw._8_8_;
  auVar43._0_8_ = param_4;
  uStack_90 = in_s0_qw._0_4_;
  uStack_8c = in_s0_qw._4_4_;
  uStack_88 = in_s0_qw._8_4_;
  uStack_84 = in_s0_qw._12_4_;
  if (param_4 < 0) {
    puStack_c0 = (undefined *)0x0;
  }
  else {
    puStack_c0 = &DAT_00241b40 + (int)param_4 * 0x150;
  }
  iRam002901b0 = iRam002901b0 + 1;
  uStack_d0 = param_2;
  iStack_cc = param_5;
  uStack_c8 = param_6;
  uStack_c4 = param_7;
  uVar11 = FUN_00118cd0(uRam002901a8);
  auVar44._8_8_ = in_s0_qw._8_8_;
  auVar44._0_8_ = (long)((int)uVar11 + 0x1f);
  FUN_00118d80(uVar11,uRam002901a8,0);
  uVar38 = auVar44._0_8_ & 0xfffffffffffffff0;
  FUN_0020c7fc(uVar38,0,0x720);
  puVar37 = (undefined1 *)uVar38;
  if (param_1 != 0) {
    iVar6 = FUN_0020e10c();
    auVar44._0_8_ = (long)(iVar6 + 1);
    uVar11 = FUN_0010d020(auVar44._0_8_);
    *(int *)(puVar37 + 4) = (int)uVar11;
    FUN_00101730(uVar11,auVar44._0_8_,0x290208);
  }
  *puVar37 = auVar43[0];
  puVar37[0x472] = 0x50;
  puVar37[3] = (char)uStack_c8;
  puVar37[1] = (char)param_3;
  *(undefined4 *)(puVar37 + 8) = uStack_d0;
  FUN_001bffc8(uVar38,1);
  if (iStack_cc != -1) {
    puVar7 = (undefined4 *)FUN_00125518();
    *(undefined4 *)(puVar37 + 0x6f4) = *puVar7;
    *(int *)(puStack_c0 + 0x14) = iStack_cc;
    *(undefined4 *)(puVar37 + 0x6f8) = puVar7[2];
    *(undefined4 *)(puVar37 + 0x6fc) = puVar7[4];
    *(undefined4 *)(puVar37 + 0x700) = puVar7[1];
    *(undefined4 *)(puVar37 + 0x704) = puVar7[3];
    *(undefined4 *)(puVar37 + 0x708) = puVar7[5];
  }
  fVar5 = FLOAT_002901e8;
  fVar40 = FLOAT_002901e4;
  if (param_3 != 0) {
    if (param_3 < 5) {
      *(float *)(puVar37 + 0x718) = 0.14999999;
      lVar13 = 0;
      *(float *)(puVar37 + 0x70c) = 0.099999994;
      iVar41 = 0x10;
      *(float *)(puVar37 + 0x710) = 0.14999999;
      *(float *)(puVar37 + 0x714) = 0.14999999;
      puVar37[0x470] = 8;
      uVar11 = FUN_0010d020(0x980);
      *(int *)(puVar37 + 0x6f0) = (int)uVar11;
      FUN_0020c7fc(uVar11,0,(uint)(byte)puVar37[0x470] * 0x130);
      iVar6 = *(int *)(puVar37 + 0x6f0);
      do {
        iVar34 = (int)lVar13;
        puVar7 = (undefined4 *)(iVar6 + iVar41);
        lVar15 = (long)*(int *)(puVar37 + 0x6f8);
        auVar44._0_8_ = (long)(int)puVar7;
        auVar43._0_8_ = (long)(int)puVar7;
        lVar23 = (long)*(int *)(puVar37 + 0x700);
        lVar22 = (long)*(int *)(puVar37 + 0x704);
        auVar31 = _pextlw(lVar22,lVar23);
        auVar14 = _pextlw(lVar15,lVar23);
        lVar26 = (long)*(int *)(puVar37 + 0x6f4);
        auVar30 = _pextlw(lVar22,lVar26);
        auVar28 = _pextlw(lVar15,lVar26);
        auVar18 = _pextlw(lVar15,lVar26);
        auVar39 = _pextlw(lVar22,lVar23);
        auVar24 = _pextlw(0,(long)*(int *)(puVar37 + 0x708));
        auVar29 = _por(in_zero_qw,auVar14);
        auVar27 = _pcpyld(auVar24,auVar14);
        auVar14 = _pextlw(0,(long)*(int *)(puVar37 + 0x6fc));
        auVar25 = _pcpyld(auVar24,auVar28);
        auVar39 = _pcpyld(auVar24,auVar39);
        auVar28 = _por(in_zero_qw,auVar30);
        auVar24 = _pcpyld(auVar24,auVar28);
        auVar29 = _pcpyld(auVar14,auVar29);
        auVar31 = _pcpyld(auVar14,auVar31);
        auVar28 = _pcpyld(auVar14,auVar18);
        auVar14 = _pcpyld(auVar14,auVar30);
        *puVar7 = auVar25._0_4_;
        puVar7[1] = auVar25._4_4_;
        puVar7[2] = auVar25._8_4_;
        puVar7[3] = auVar25._12_4_;
        puVar7[0x4c] = auVar27._0_4_;
        puVar7[0x4d] = auVar27._4_4_;
        puVar7[0x4e] = auVar27._8_4_;
        puVar7[0x4f] = auVar27._12_4_;
        puVar7[0x98] = auVar28._0_4_;
        puVar7[0x99] = auVar28._4_4_;
        puVar7[0x9a] = auVar28._8_4_;
        puVar7[0x9b] = auVar28._12_4_;
        puVar7[0xe4] = auVar29._0_4_;
        puVar7[0xe5] = auVar29._4_4_;
        puVar7[0xe6] = auVar29._8_4_;
        puVar7[0xe7] = auVar29._12_4_;
        puVar7[0x130] = auVar24._0_4_;
        puVar7[0x131] = auVar24._4_4_;
        puVar7[0x132] = auVar24._8_4_;
        puVar7[0x133] = auVar24._12_4_;
        puVar7[0x17c] = auVar39._0_4_;
        puVar7[0x17d] = auVar39._4_4_;
        puVar7[0x17e] = auVar39._8_4_;
        puVar7[0x17f] = auVar39._12_4_;
        puVar7[0x1c8] = auVar14._0_4_;
        puVar7[0x1c9] = auVar14._4_4_;
        puVar7[0x1ca] = auVar14._8_4_;
        puVar7[0x1cb] = auVar14._12_4_;
        puVar7[0x214] = auVar31._0_4_;
        puVar7[0x215] = auVar31._4_4_;
        puVar7[0x216] = auVar31._8_4_;
        puVar7[0x217] = auVar31._12_4_;
        iVar9 = 0;
        if (puVar37[0x470] != '\0') {
          fVar40 = 0.29999998;
          auVar43._0_8_ = 1;
          auVar14._8_8_ = 0;
          auVar14._0_8_ = auVar44._8_8_;
          auVar44 = auVar14 << 0x40;
          do {
            iVar35 = auVar44._0_4_;
            iVar6 = iVar35 + iVar6;
            *(undefined1 *)(iVar6 + 5) = 1;
            *(float *)(iVar6 + 0x70) = fVar40;
            iVar34 = *(int *)(puVar37 + 0x6f0);
            *(float *)(iVar6 + 0x74) = 0.59999996;
            *(char *)(iVar35 + iVar34 + 4) = (char)iVar9;
            iVar9 = iVar9 + 1;
            iVar6 = *(int *)(puVar37 + 0x6f0);
            *(undefined4 *)(iVar35 + iVar6) = auVar43._0_4_;
            if (((undefined4 *)(iVar35 + iVar6))[0x45] == 0) {
              uVar8 = FUN_001348a8();
              iVar6 = *(int *)(puVar37 + 0x6f0);
              *(undefined4 *)(auVar44._0_4_ + iVar6 + 0x114) = uVar8;
            }
            iVar34 = (int)lVar13;
            auVar44._0_8_ = (long)(auVar44._0_4_ + 0x130);
          } while (iVar9 < (int)(uint)(byte)puVar37[0x470]);
        }
        lVar13 = (long)(iVar34 + 1);
        iVar41 = iVar41 + 0x10;
      } while (lVar13 < 5);
    }
    else if (param_3 == 5) {
      iVar6 = 0x10;
      iStack_bc = 0;
      *(float *)(puVar37 + 0x710) = FLOAT_002901e0;
      *(float *)(puVar37 + 0x70c) = 0.01;
      *(float *)(puVar37 + 0x714) = fVar40;
      *(float *)(puVar37 + 0x718) = fVar5;
      iVar41 = 0;
      puVar37[0x470] = 0xc;
      uVar11 = FUN_0010d020(0xe40);
      *(int *)(puVar37 + 0x6f0) = (int)uVar11;
      iStack_a0 = 0x160;
      FUN_0020c7fc(uVar11,0,(uint)(byte)puVar37[0x470] * 0x130);
      auVar24 = _pextlw(0x3f800000,(long)iVar41);
      auVar14 = _pextlw((long)iVar41,(long)iVar41);
      auVar24 = _por(in_zero_qw,auVar24);
      auVar39 = _pcpyld(auVar14,auVar24);
      auVar24 = _por(in_zero_qw,auVar39);
      auVar14 = _por(in_zero_qw,auVar24);
      uStack_b0 = auVar14._0_4_;
      uStack_ac = auVar14._4_4_;
      uStack_a8 = auVar14._8_4_;
      uStack_a4 = auVar14._12_4_;
      do {
        iVar9 = *(int *)(puVar37 + 0x6f0);
        iVar35 = 4;
        iVar36 = 0x4c0;
        iVar34 = iVar9 + iVar6;
        auVar43._0_8_ = (long)iVar34;
        auVar44._0_8_ = auVar43._0_8_;
        auVar28 = _pextlw((long)*(int *)(puVar37 + 0x6f8),(long)*(int *)(puVar37 + 0x700));
        auVar33 = _pextlw((long)*(int *)(puVar37 + 0x704),(long)*(int *)(puVar37 + 0x700));
        auVar32 = _pextlw((long)*(int *)(puVar37 + 0x704),(long)*(int *)(puVar37 + 0x6f4));
        auVar30 = _pextlw((long)*(int *)(puVar37 + 0x6f8),(long)*(int *)(puVar37 + 0x6f4));
        auVar14 = _pextlw((long)iVar41,(long)*(int *)(puVar37 + 0x708));
        auVar31 = _por(in_zero_qw,auVar28);
        auVar29 = _pcpyld(auVar14,auVar28);
        auVar28 = _pextlw((long)iVar41,(long)*(int *)(puVar37 + 0x6fc));
        auVar18 = _por(in_zero_qw,auVar33);
        auVar18 = _pcpyld(auVar14,auVar18);
        auVar25 = _por(in_zero_qw,auVar30);
        auVar25 = _pcpyld(auVar28,auVar25);
        auVar27 = _por(in_zero_qw,auVar32);
        auVar27 = _pcpyld(auVar14,auVar27);
        auVar14 = _pcpyld(auVar14,auVar30);
        auVar33 = _pcpyld(auVar28,auVar33);
        auVar30 = _pcpyld(auVar28,auVar31);
        auVar28 = _pcpyld(auVar28,auVar32);
        *(int *)(iVar34 + 0x4c0) = auVar14._0_4_;
        *(int *)(iVar34 + 0x4c4) = auVar14._4_4_;
        *(int *)(iVar34 + 0x4c8) = auVar14._8_4_;
        *(int *)(iVar34 + 0x4cc) = auVar14._12_4_;
        *(int *)(iVar34 + 0x5f0) = auVar29._0_4_;
        *(int *)(iVar34 + 0x5f4) = auVar29._4_4_;
        *(int *)(iVar34 + 0x5f8) = auVar29._8_4_;
        *(int *)(iVar34 + 0x5fc) = auVar29._12_4_;
        *(int *)(iVar34 + 0x720) = auVar25._0_4_;
        *(int *)(iVar34 + 0x724) = auVar25._4_4_;
        *(int *)(iVar34 + 0x728) = auVar25._8_4_;
        *(int *)(iVar34 + 0x72c) = auVar25._12_4_;
        *(int *)(iVar34 + 0x850) = auVar30._0_4_;
        *(int *)(iVar34 + 0x854) = auVar30._4_4_;
        *(int *)(iVar34 + 0x858) = auVar30._8_4_;
        *(int *)(iVar34 + 0x85c) = auVar30._12_4_;
        *(int *)(iVar34 + 0x980) = auVar27._0_4_;
        *(int *)(iVar34 + 0x984) = auVar27._4_4_;
        *(int *)(iVar34 + 0x988) = auVar27._8_4_;
        *(int *)(iVar34 + 0x98c) = auVar27._12_4_;
        *(int *)(iVar34 + 0xab0) = auVar18._0_4_;
        *(int *)(iVar34 + 0xab4) = auVar18._4_4_;
        *(int *)(iVar34 + 0xab8) = auVar18._8_4_;
        *(int *)(iVar34 + 0xabc) = auVar18._12_4_;
        *(int *)(iVar34 + 0xbe0) = auVar28._0_4_;
        *(int *)(iVar34 + 0xbe4) = auVar28._4_4_;
        *(int *)(iVar34 + 0xbe8) = auVar28._8_4_;
        *(int *)(iVar34 + 0xbec) = auVar28._12_4_;
        *(int *)(iVar34 + 0xd10) = auVar33._0_4_;
        *(int *)(iVar34 + 0xd14) = auVar33._4_4_;
        *(int *)(iVar34 + 0xd18) = auVar33._8_4_;
        *(int *)(iVar34 + 0xd1c) = auVar33._12_4_;
        do {
          if (iVar35 < 4) {
LAB_001bc1b4:
            *(float *)(iVar36 + iVar9 + 0x70) = 0.005;
          }
          else if (iVar35 < 6) {
LAB_001bc1a0:
            *(float *)(iVar36 + iVar9 + 0x70) = 0.39999998;
          }
          else {
            if (9 < iVar35) goto LAB_001bc1b4;
            if (7 < iVar35) goto LAB_001bc1a0;
            *(float *)(iVar36 + iVar9 + 0x70) = 0.005;
          }
          if (7 < iVar35) {
            *(float *)(iVar36 + iVar9 + 0x74) = 0.005;
          }
          else {
            *(undefined4 *)(iVar36 + iVar9 + 0x74) = 0;
          }
          *(undefined1 *)(iVar36 + iVar9 + 5) = 1;
          *(char *)(iVar36 + *(int *)(puVar37 + 0x6f0) + 4) = (char)iVar35;
          iVar9 = *(int *)(puVar37 + 0x6f0);
          *(undefined4 *)(iVar36 + iVar9) = 1;
          if (((undefined4 *)(iVar36 + iVar9))[0x45] == 0) {
            uVar8 = FUN_001348a8();
            iVar9 = *(int *)(puVar37 + 0x6f0);
            iVar34 = iVar36 + iVar9;
            *(undefined4 *)(iVar34 + 0x90) = uStack_b0;
            *(undefined4 *)(iVar34 + 0x94) = uStack_ac;
            *(undefined4 *)(iVar34 + 0x98) = uStack_a8;
            *(undefined4 *)(iVar34 + 0x9c) = uStack_a4;
            *(undefined4 *)(iVar34 + 0x114) = uVar8;
            uVar8 = *(undefined4 *)(puVar37 + 0x50);
            uVar2 = *(undefined4 *)(puVar37 + 0x54);
            uVar3 = *(undefined4 *)(puVar37 + 0x58);
            uVar4 = *(undefined4 *)(puVar37 + 0x5c);
            *(int *)(iVar34 + 0x110) = iVar41;
            *(undefined4 *)(iVar34 + 0xa0) = uVar8;
            *(undefined4 *)(iVar34 + 0xa4) = uVar2;
            *(undefined4 *)(iVar34 + 0xa8) = uVar3;
            *(undefined4 *)(iVar34 + 0xac) = uVar4;
            *(int *)(iVar34 + 0x100) = iVar41;
            uVar8 = *(undefined4 *)(puVar37 + 0x600);
            uVar2 = *(undefined4 *)(puVar37 + 0x604);
            uVar3 = *(undefined4 *)(puVar37 + 0x608);
            uVar4 = *(undefined4 *)(puVar37 + 0x60c);
            *(int *)(iVar34 + 0x104) = iVar41;
            *(undefined4 *)(iVar34 + 0xb0) = uVar8;
            *(undefined4 *)(iVar34 + 0xb4) = uVar2;
            *(undefined4 *)(iVar34 + 0xb8) = uVar3;
            *(undefined4 *)(iVar34 + 0xbc) = uVar4;
            *(int *)(iVar34 + 0x108) = iVar41;
            auVar14 = *(undefined1 (*) [16])(puVar37 + 0x600);
            *(int *)(iVar34 + 0x10c) = iVar41;
            *(int *)(iVar34 + 0xc0) = auVar14._0_4_;
            *(int *)(iVar34 + 0xc4) = auVar14._4_4_;
            *(int *)(iVar34 + 200) = auVar14._8_4_;
            *(int *)(iVar34 + 0xcc) = auVar14._12_4_;
            auVar14 = *(undefined1 (*) [16])(puVar37 + 0x600);
            *(int *)(iVar34 + 0xf0) = auVar39._0_4_;
            *(int *)(iVar34 + 0xf4) = auVar39._4_4_;
            *(int *)(iVar34 + 0xf8) = auVar39._8_4_;
            *(int *)(iVar34 + 0xfc) = auVar39._12_4_;
            *(int *)(iVar34 + 0xe0) = auVar14._0_4_;
            *(int *)(iVar34 + 0xe4) = auVar14._4_4_;
            *(int *)(iVar34 + 0xe8) = auVar14._8_4_;
            *(int *)(iVar34 + 0xec) = auVar14._12_4_;
            *(int *)(iVar34 + 0xd0) = auVar24._0_4_;
            *(int *)(iVar34 + 0xd4) = auVar24._4_4_;
            *(int *)(iVar34 + 0xd8) = auVar24._8_4_;
            *(int *)(iVar34 + 0xdc) = auVar24._12_4_;
          }
          iVar35 = iVar35 + 1;
          iVar36 = iVar36 + 0x130;
        } while (iVar35 < 0xc);
        iVar34 = 0;
        while( true ) {
          uVar12 = auVar43._8_8_;
          iVar35 = iVar34 * 4;
          uVar11 = auVar44._8_8_;
          iVar36 = iVar34 * 0x130;
          *(undefined1 *)(iVar36 + iVar9 + 5) = 1;
          iVar9 = iVar36 + *(int *)(puVar37 + 0x6f0);
          *(float *)(iVar9 + 0x70) = 0.29999998;
          *(undefined4 *)(iVar9 + 0x74) = 0;
          if (*(int *)(iVar9 + 0x120) == 0) {
            uVar12 = FUN_0010d020(0x180);
            *(int *)(iVar36 + *(int *)(puVar37 + 0x6f0) + 0x120) = (int)uVar12;
            FUN_0020c7fc(uVar12,0,0x180);
            uVar12 = auVar43._8_8_;
          }
          auVar43._0_8_ = (long)((int)&PTR_s_HUB_FRONT_LEFT_002432e0 + iVar35);
          auVar43._8_8_ = uVar12;
          lVar13 = FUN_00124e98(uStack_c4,
                                *(undefined4 *)((int)&PTR_s_HUB_FRONT_LEFT_002432e0 + iVar35));
          auVar44._8_8_ = uVar11;
          auVar44._0_8_ = lVar13;
          if (lVar13 == -1) {
                    /* WARNING: Subroutine does not return */
            FUN_00105888(0x282c40,0x2fc,0x282c60,*auVar43._0_4_,*(undefined4 *)(puVar37 + 4));
          }
          uVar11 = FUN_00121d98(*(undefined4 *)(puStack_c0 + 0x14));
          uStack_e4 = auVar44._0_4_;
          uStack_f0 = (undefined4)uVar11;
          uStack_e8 = 0;
          lVar13 = FUN_001231c0(&uStack_f0);
          if (lVar13 == 1) {
            *(char *)(iVar36 + *(int *)(puVar37 + 0x6f0) + 4) = (char)iVar34;
            iVar9 = *(int *)(puVar37 + 0x6f0);
            puVar7 = (undefined4 *)(iVar36 + iVar9);
            *puVar7 = 2;
            iVar35 = puVar7[0x48];
            iVar1 = puVar7[0x45];
            piVar10 = (int *)(iVar35 + 0xc + iStack_a0);
            *piVar10 = 0;
            iVar42 = *piVar10;
            lVar13 = (long)iVar42;
            auVar28 = _pextlw(0x3f800000,lVar13);
            auVar44 = _pextlw(lVar13,lVar13);
            auVar43 = _por(in_zero_qw,auVar28);
            auVar18 = _pextlw(lVar13,0x3f800000);
            auVar14 = _por(in_zero_qw,auVar44);
            auVar28 = _pcpyld(auVar44,auVar28);
            auVar14 = _pcpyld(auVar18,auVar14);
            *(int *)(iVar35 + 0x70) = auVar14._0_4_;
            *(int *)(iVar35 + 0x74) = auVar14._4_4_;
            *(int *)(iVar35 + 0x78) = auVar14._8_4_;
            *(int *)(iVar35 + 0x7c) = auVar14._12_4_;
            *(int *)(iVar35 + 0xb0) = auVar28._0_4_;
            *(int *)(iVar35 + 0xb4) = auVar28._4_4_;
            *(int *)(iVar35 + 0xb8) = auVar28._8_4_;
            *(int *)(iVar35 + 0xbc) = auVar28._12_4_;
            if (iVar1 == 0) {
              uVar8 = FUN_001348a8();
              iVar9 = *(int *)(puVar37 + 0x6f0);
              auVar14 = _por(in_zero_qw,auVar43);
              auVar14 = _pcpyld(auVar44,auVar14);
              iVar35 = iVar36 + iVar9;
              uVar16 = auVar14._0_4_;
              *(undefined4 *)(iVar35 + 0x90) = uVar16;
              uVar19 = auVar14._4_4_;
              *(undefined4 *)(iVar35 + 0x94) = uVar19;
              uVar20 = auVar14._8_4_;
              *(undefined4 *)(iVar35 + 0x98) = uVar20;
              uVar21 = auVar14._12_4_;
              *(undefined4 *)(iVar35 + 0x9c) = uVar21;
              *(undefined4 *)(iVar35 + 0x114) = uVar8;
              uVar8 = *(undefined4 *)(puVar37 + 0x50);
              uVar2 = *(undefined4 *)(puVar37 + 0x54);
              uVar3 = *(undefined4 *)(puVar37 + 0x58);
              uVar4 = *(undefined4 *)(puVar37 + 0x5c);
              *(int *)(iVar35 + 0x110) = iVar42;
              *(undefined4 *)(iVar35 + 0xa0) = uVar8;
              *(undefined4 *)(iVar35 + 0xa4) = uVar2;
              *(undefined4 *)(iVar35 + 0xa8) = uVar3;
              *(undefined4 *)(iVar35 + 0xac) = uVar4;
              *(int *)(iVar35 + 0x100) = iVar42;
              uVar8 = *(undefined4 *)(puVar37 + 0x600);
              uVar2 = *(undefined4 *)(puVar37 + 0x604);
              uVar3 = *(undefined4 *)(puVar37 + 0x608);
              uVar4 = *(undefined4 *)(puVar37 + 0x60c);
              *(int *)(iVar35 + 0x104) = iVar42;
              *(undefined4 *)(iVar35 + 0xb0) = uVar8;
              *(undefined4 *)(iVar35 + 0xb4) = uVar2;
              *(undefined4 *)(iVar35 + 0xb8) = uVar3;
              *(undefined4 *)(iVar35 + 0xbc) = uVar4;
              *(int *)(iVar35 + 0x108) = iVar42;
              uVar8 = *(undefined4 *)(puVar37 + 0x600);
              uVar2 = *(undefined4 *)(puVar37 + 0x604);
              uVar3 = *(undefined4 *)(puVar37 + 0x608);
              uVar4 = *(undefined4 *)(puVar37 + 0x60c);
              *(int *)(iVar35 + 0x10c) = iVar42;
              *(undefined4 *)(iVar35 + 0xc0) = uVar8;
              *(undefined4 *)(iVar35 + 0xc4) = uVar2;
              *(undefined4 *)(iVar35 + 200) = uVar3;
              *(undefined4 *)(iVar35 + 0xcc) = uVar4;
              auVar14 = *(undefined1 (*) [16])(puVar37 + 0x600);
              *(undefined4 *)(iVar35 + 0xd0) = uVar16;
              *(undefined4 *)(iVar35 + 0xd4) = uVar19;
              *(undefined4 *)(iVar35 + 0xd8) = uVar20;
              *(undefined4 *)(iVar35 + 0xdc) = uVar21;
              *(int *)(iVar35 + 0xe0) = auVar14._0_4_;
              *(int *)(iVar35 + 0xe4) = auVar14._4_4_;
              *(int *)(iVar35 + 0xe8) = auVar14._8_4_;
              *(int *)(iVar35 + 0xec) = auVar14._12_4_;
              *(undefined4 *)(iVar35 + 0xf0) = uVar16;
              *(undefined4 *)(iVar35 + 0xf4) = uVar19;
              *(undefined4 *)(iVar35 + 0xf8) = uVar20;
              *(undefined4 *)(iVar35 + 0xfc) = uVar21;
            }
            auVar18 = _qmtc2(iVar42);
            auVar28 = _lqc2(*(undefined1 (*) [16])(iStack_ec + 0x10));
            iVar35 = *(int *)(iVar36 + iVar9 + 0x120);
            auVar14 = _sqc2(auVar28);
            *(undefined1 (*) [16])(iVar36 + iVar9 + iVar6) = auVar14;
            auVar14 = _sqc2(auVar28);
            *(undefined1 (*) [16])(iVar35 + 0x50) = auVar14;
            auVar14 = _vmulbc(in_vf0,auVar18);
            auVar14 = _sqc2(auVar14);
            *(undefined1 (*) [16])(iVar35 + 0x50) = auVar14;
          }
          iVar34 = iVar34 + 1;
          FUN_00121de0(uVar11);
          if (3 < iVar34) break;
          iVar9 = *(int *)(puVar37 + 0x6f0);
        }
        iVar6 = iVar6 + 0x10;
        iStack_bc = iStack_bc + 1;
        iStack_a0 = iStack_a0 + 4;
      } while (iStack_bc < 5);
      iVar6 = *(int *)(puVar37 + 0x6f0);
      iStack_bc = 4;
      pauVar17 = (undefined1 (*) [16])(iVar6 + 0x3a0);
      auVar44 = _qmtc2(0);
      fVar40 = *(float *)(*(int *)(iVar6 + 0x120) + 0x50);
      iVar41 = *(int *)(iVar6 + 0x250);
      _qmtc2(fVar40);
      auVar43 = _qmtc2(-fVar40);
      auVar43 = _vaddbc(in_vf0,auVar43);
      iVar9 = *(int *)(iVar6 + 0x380);
      auVar43 = _sqc2(auVar43);
      *(undefined1 (*) [16])(iVar41 + 0x50) = auVar43;
      auVar43 = _vmulbc(in_vf0,auVar44);
      auVar43 = _sqc2(auVar43);
      *(undefined1 (*) [16])(iVar41 + 0x50) = auVar43;
      iVar41 = *(int *)(iVar6 + 0x4b0);
      fVar40 = *(float *)(iVar9 + 0x50);
      _qmtc2(fVar40);
      auVar43 = _qmtc2(-fVar40);
      auVar43 = _vaddbc(in_vf0,auVar43);
      auVar43 = _sqc2(auVar43);
      *(undefined1 (*) [16])(iVar41 + 0x50) = auVar43;
      auVar43 = _vmulbc(in_vf0,auVar44);
      auVar43 = _sqc2(auVar43);
      *(undefined1 (*) [16])(iVar41 + 0x50) = auVar43;
      do {
        auVar43 = _lqc2(pauVar17[-0x39]);
        auVar24 = _lqc2(pauVar17[-0x13]);
        auVar14 = _qmfc2(auVar43._0_4_);
        auVar44 = _qmfc2(auVar24._0_4_);
        auVar43 = _sqc2(auVar43);
        pauVar17[-0x26] = auVar43;
        auVar43 = _sqc2(auVar24);
        *pauVar17 = auVar43;
        auVar43 = _qmtc2(-auVar14._0_4_);
        auVar44 = _qmtc2(-auVar44._0_4_);
        auVar43 = _vaddbc(in_vf0,auVar43);
        iStack_bc = iStack_bc + -1;
        auVar44 = _vaddbc(in_vf0,auVar44);
        auVar43 = _sqc2(auVar43);
        pauVar17[-0x26] = auVar43;
        auVar43 = _sqc2(auVar44);
        *pauVar17 = auVar43;
        pauVar17 = pauVar17 + 1;
      } while (-1 < iStack_bc);
      *(undefined1 *)(iVar6 + 8) = 3;
      *(undefined1 *)(*(int *)(puVar37 + 0x6f0) + 0x138) = 4;
      *(undefined1 *)(*(int *)(puVar37 + 0x6f0) + 0x268) = 5;
      *(undefined1 *)(*(int *)(puVar37 + 0x6f0) + 0x398) = 6;
    }
  }
  FUN_001bc5d8(uVar38,uStack_d0,iStack_cc,uStack_c8);
  return uVar38;
}

