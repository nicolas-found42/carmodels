
void FUN_0021fd50(float param_1,float param_2,float param_3,float param_4,undefined4 param_5,
                 undefined4 param_6,undefined4 param_7,int param_8,long param_9,int param_10,
                 int param_11,uint param_12,long param_13)

{
  undefined8 *puVar1;
  ulong *puVar2;
  undefined4 *puVar3;
  undefined1 (*pauVar4) [16];
  int *piVar5;
  int *piVar6;
  undefined1 in_zero_qw [16];
  float *pfVar7;
  long lVar8;
  ulong uVar9;
  undefined1 auVar10 [16];
  ulong uVar11;
  undefined1 auVar12 [16];
  int iVar13;
  undefined1 auVar14 [16];
  undefined1 auVar15 [16];
  undefined1 auVar16 [16];
  int iVar17;
  undefined1 auVar18 [16];
  undefined1 auVar19 [16];
  long lVar20;
  long lVar21;
  undefined4 uVar22;
  long lVar23;
  undefined4 uVar24;
  undefined4 uVar25;
  undefined4 uVar26;
  float fVar27;
  int iVar28;
  float fVar29;
  int iVar30;
  float fVar31;
  float fVar32;
  undefined1 auVar33 [16];
  undefined1 auVar34 [16];
  undefined1 auVar35 [16];
  undefined1 auVar36 [16];
  undefined1 auStack_210 [48];
  undefined4 uStack_1e0;
  undefined4 uStack_1dc;
  undefined4 uStack_1d8;
  undefined4 uStack_1d4;
  undefined4 uStack_1d0;
  undefined4 uStack_1cc;
  undefined4 uStack_1c8;
  undefined4 uStack_1c4;
  undefined4 uStack_1c0;
  undefined4 uStack_1bc;
  undefined4 uStack_1b8;
  undefined4 uStack_1b4;
  undefined1 auStack_190 [48];
  undefined4 uStack_160;
  undefined4 uStack_15c;
  undefined4 uStack_158;
  undefined4 uStack_154;
  undefined1 auStack_150 [16];
  undefined1 auStack_140 [16];
  undefined1 auStack_130 [16];
  undefined1 auStack_120 [16];
  float fStack_110;
  float fStack_10c;
  float fStack_108;
  float fStack_104;
  float fStack_100;
  float fStack_fc;
  int iStack_f8;
  int iStack_f4;
  int iStack_f0;
  int iStack_ec;
  int iStack_e8;
  uint uStack_e0;
  int iStack_d0;
  int iStack_c0;
  int iStack_bc;
  ulong uStack_b8;
  
  if (iRam0028ef00 != 0) {
    iStack_f8 = param_8;
    iStack_f4 = param_10;
    lVar8 = FUN_0022a328();
    if (lVar8 == 0) {
      if (iStack_f8 == 0) {
        FUN_001154d0(auStack_150,&fStack_10c);
      }
      else {
        FUN_00110970(param_5,param_6,&fStack_110);
        auVar36 = _qmtc2(param_7);
        _vcallms(0x268);
        auVar10 = _qmfc2(auVar36._0_4_);
        auVar19 = _qmfc2(auVar36._0_4_);
        auVar18 = _prot3w(auVar10);
        FUN_001154d0(auStack_210);
        lVar23 = (long)(int)auStack_190;
        FUN_001154d0(lVar23);
        lVar8 = (long)(int)&uStack_1d0;
        FUN_001154d0(lVar8);
        auVar15 = _pextlw((long)(int)fStack_10c,(long)(int)fStack_110);
        auVar12 = _pextlw(0,0);
        auVar10 = _pextlw(auVar18._0_8_,(long)(int)-auVar19._0_4_);
        auVar14 = _pcpyld(auVar12,auVar10);
        auVar36 = _pextlw(0x3f800000,0);
        auVar10 = _pextlw((long)(int)-fStack_10c,(long)(int)-fStack_110);
        auVar16 = _pcpyld(auVar36,auVar15);
        auVar15 = _pextlw(auVar19._0_8_,auVar18._0_8_);
        auVar10 = _pcpyld(auVar36,auVar10);
        auVar36 = _pcpyld(auVar12,auVar15);
        uStack_1e0 = auVar10._0_4_;
        uStack_1dc = auVar10._4_4_;
        uStack_1d8 = auVar10._8_4_;
        uStack_1d4 = auVar10._12_4_;
        uStack_160 = auVar16._0_4_;
        uStack_15c = auVar16._4_4_;
        uStack_158 = auVar16._8_4_;
        uStack_154 = auVar16._12_4_;
        uStack_1d0 = auVar36._0_4_;
        uStack_1cc = auVar36._4_4_;
        uStack_1c8 = auVar36._8_4_;
        uStack_1c4 = auVar36._12_4_;
        uStack_1c0 = auVar14._0_4_;
        uStack_1bc = auVar14._4_4_;
        uStack_1b8 = auVar14._8_4_;
        uStack_1b4 = auVar14._12_4_;
        FUN_00115560(auStack_150,auStack_210,lVar8);
        FUN_00115560(auStack_150,auStack_150,lVar23);
      }
      if (param_3 < param_1) {
        iStack_c0 = -8;
      }
      else {
        iStack_c0 = 0;
      }
      if (param_4 < param_2) {
        iStack_bc = -8;
      }
      else {
        iStack_bc = 0;
      }
      if (param_13 == 0) {
        FUN_0010fa20(10,1);
        FUN_0010fa20(0xb,1);
      }
      else {
        FUN_0010fa20(10,2);
        FUN_0010fa20(0xb,2);
      }
      FUN_00110618();
      piVar5 = piRam0028eeb8;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0x1000000000000003;
      *piVar5 = (int)(puVar1 + 1);
      piVar5 = piRam0028eeb8;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0xe;
      *piVar5 = (int)(puVar1 + 1);
      piVar5 = piRam0028eeb8;
      if (iStack_f8 == 0) {
        iStack_d0 = 2;
        uStack_e0 = 0x116;
      }
      else {
        iStack_d0 = 4;
        uStack_e0 = 0x114;
      }
      if (param_9 == 1) {
        uStack_e0 = uStack_e0 | 0x40;
        puVar1 = (undefined8 *)*piRam0028eeb8;
        *puVar1 = 0x30000;
        *piVar5 = (int)(puVar1 + 1);
      }
      else {
        puVar2 = (ulong *)*piRam0028eeb8;
        *piRam0028eeb8 = (int)(puVar2 + 1);
        *puVar2 = param_9 << 1 | ((long)(iStack_f4 + 1 >> 1) & 0xffU) << 4 | 0x30001;
      }
      piVar5 = piRam0028eeb8;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0x47;
      *piVar5 = (int)(puVar1 + 1);
      uVar11 = (ulong)DAT_002324ec;
      puVar2 = (ulong *)*piRam0028eeb8;
      uVar9 = (ulong)DAT_002324fa;
      *piRam0028eeb8 = (int)(puVar2 + 1);
      *puVar2 = uVar9 | (long)(uVar11 << 0x30) >> 0x18 | 0x100000000;
      piVar5 = piRam0028eeb8;
      iStack_f0 = 0;
      iStack_e8 = 0;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0x4e;
      *piVar5 = (int)(puVar1 + 1);
      piVar5 = piRam0028eeb8;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0x44;
      *piVar5 = (int)(puVar1 + 1);
      piVar5 = piRam0028eeb8;
      puVar1 = (undefined8 *)*piRam0028eeb8;
      *puVar1 = 0x42;
      *piVar5 = (int)(puVar1 + 1);
      FUN_00110148();
      FUN_00110688();
      FUN_00110970(param_1,param_2,&fStack_108,&fStack_104);
      FUN_00110970(param_3,param_4,&fStack_100,&fStack_fc);
      auVar36 = _pextlw((ulong)(byte)((int)((param_12 >> 8 & 0xff) + 1) >> 1),
                        (long)((int)((param_12 >> 0x10 & 0xff) + 1) >> 1));
      iVar13 = *(int *)(param_11 + 8);
      fVar32 = ((fStack_100 - fStack_108) * (float)*(int *)(param_11 + 0xc)) /
               (float)*(int *)(param_11 + 0x14);
      auVar10 = _pextlw((ulong)(byte)((int)((param_12 >> 0x18) + 1) >> 1),
                        (ulong)(byte)((int)((param_12 & 0xff) + 1) >> 1));
      auVar10 = _pcpyld(auVar10,auVar36);
      fVar31 = ((fStack_fc - fStack_104) * (float)*(int *)(param_11 + 0x10)) /
               (float)*(int *)(param_11 + 0x18);
      fStack_10c = fStack_104;
      if (0 < iVar13) {
        iVar17 = *(int *)(param_11 + 4);
        do {
          fStack_110 = fStack_108;
          iStack_ec = 0;
          if (0 < iVar17) {
            uStack_b8 = (long)iStack_d0 | (long)(int)uStack_e0 << 0x2f | 0x3000400000000000;
            auVar12 = _pextlw(0x3f800000,0);
            auVar15 = _pextlw(0,0);
            auVar36 = _pextlw(0,0);
            do {
              iVar17 = iStack_f0 * 0x10;
              FUN_00220fe0(*(undefined4 *)(iVar17 + *(int *)(param_11 + 0x44) + 8),1);
              pfVar7 = (float *)(iVar17 + *(int *)(param_11 + 0x44));
              iVar30 = (int)(pfVar7[1] * (float)*(int *)(param_11 + 0x10));
              iVar28 = (int)(*pfVar7 * (float)*(int *)(param_11 + 0xc));
              FUN_00110618();
              piVar5 = piRam0028eeb8;
              puVar1 = (undefined8 *)*piRam0028eeb8;
              *puVar1 = 0x1000000000000001;
              *piVar5 = (int)(puVar1 + 1);
              piVar5 = piRam0028eeb8;
              iVar13 = *(int *)(param_11 + 0x44);
              puVar1 = (undefined8 *)*piRam0028eeb8;
              *puVar1 = 0xe;
              *piVar5 = (int)(puVar1 + 1);
              piVar5 = piRam0028eeb8;
              pfVar7 = (float *)(iVar17 + iVar13);
              puVar2 = (ulong *)*piRam0028eeb8;
              auVar14 = _por(in_zero_qw,auVar15);
              lVar20 = (long)(iVar28 * 0x10 + iStack_c0);
              *puVar2 = (long)(iVar30 + -1) << 0x22 | (long)(iVar28 + -1) << 0xe | 10U;
              *piVar5 = (int)(puVar2 + 1);
              piVar5 = piRam0028eeb8;
              lVar21 = (long)(iVar30 * 0x10 + iStack_bc);
              fVar29 = *pfVar7;
              auVar14 = _pcpyld(auVar36,auVar14);
              puVar1 = (undefined8 *)*piRam0028eeb8;
              *puVar1 = 8;
              *piVar5 = (int)(puVar1 + 1);
              piVar5 = piRam0028eeb8;
              puVar2 = (ulong *)*piRam0028eeb8;
              auVar16 = _lqc2(auStack_120);
              *puVar2 = uStack_b8;
              *piVar5 = (int)(puVar2 + 1);
              piVar5 = piRam0028eeb8;
              fVar27 = pfVar7[1];
              puVar1 = (undefined8 *)*piRam0028eeb8;
              auVar34 = _lqc2(auStack_150);
              auVar19 = _lqc2(auStack_140);
              auVar18 = _lqc2(auStack_130);
              *puVar1 = 0x513;
              *piVar5 = (int)(puVar1 + 1);
              piVar5 = piRam0028eeb8;
              lVar23 = (long)(int)(fStack_110 + fVar32 * fVar29);
              puVar3 = (undefined4 *)*piRam0028eeb8;
              *puVar3 = auVar14._0_4_;
              puVar3[1] = auVar14._4_4_;
              puVar3[2] = auVar14._8_4_;
              puVar3[3] = auVar14._12_4_;
              piVar6 = piRam0028eeb8;
              auVar14 = _pextlw((long)(int)fStack_10c,(long)(int)fStack_110);
              *piVar5 = (int)(puVar3 + 4);
              auVar14 = _pcpyld(auVar12,auVar14);
              auVar14 = _qmtc2(auVar14._0_4_);
              _vmulabc(auVar34,auVar14);
              _vmaddabc(auVar19,auVar14);
              _vmaddabc(auVar18,auVar14);
              auVar14 = _vmaddbc(auVar16,auVar14);
              puVar3 = (undefined4 *)*piVar6;
              auVar14 = _vftoi0(auVar14);
              uVar22 = auVar10._0_4_;
              *puVar3 = uVar22;
              uVar24 = auVar10._4_4_;
              puVar3[1] = uVar24;
              uVar25 = auVar10._8_4_;
              puVar3[2] = uVar25;
              uVar26 = auVar10._12_4_;
              puVar3[3] = uVar26;
              *piVar6 = (int)(puVar3 + 4);
              piVar5 = piRam0028eeb8;
              lVar8 = (long)(int)(fStack_10c + fVar31 * fVar27);
              pauVar4 = (undefined1 (*) [16])*piRam0028eeb8;
              auVar14 = _sqc2(auVar14);
              *pauVar4 = auVar14;
              *piVar5 = (int)(pauVar4 + 1);
              piVar5 = piRam0028eeb8;
              if (iStack_f8 != 0) {
                auVar14 = _pextlw(0,lVar20);
                auVar14 = _pcpyld(auVar36,auVar14);
                puVar3 = (undefined4 *)*piRam0028eeb8;
                auVar35 = _lqc2(auStack_150);
                auVar33 = _lqc2(auStack_140);
                auVar34 = _lqc2(auStack_130);
                auVar19 = _lqc2(auStack_120);
                *puVar3 = auVar14._0_4_;
                puVar3[1] = auVar14._4_4_;
                puVar3[2] = auVar14._8_4_;
                puVar3[3] = auVar14._12_4_;
                *piVar5 = (int)(puVar3 + 4);
                piVar5 = piRam0028eeb8;
                auVar16 = _pextlw((long)(int)fStack_10c,lVar23);
                auVar14 = _pextlw(lVar21,0);
                auVar18 = _pcpyld(auVar12,auVar16);
                auVar16 = _pcpyld(auVar36,auVar14);
                puVar3 = (undefined4 *)*piRam0028eeb8;
                auVar14 = _qmtc2(auVar18._0_4_);
                _vmulabc(auVar35,auVar14);
                _vmaddabc(auVar33,auVar14);
                _vmaddabc(auVar34,auVar14);
                auVar14 = _vmaddbc(auVar19,auVar14);
                auVar18 = _vftoi0(auVar14);
                *puVar3 = uVar22;
                puVar3[1] = uVar24;
                puVar3[2] = uVar25;
                puVar3[3] = uVar26;
                *piVar5 = (int)(puVar3 + 4);
                piVar5 = piRam0028eeb8;
                auVar14 = _pextlw(lVar8,(long)(int)fStack_110);
                auVar14 = _pcpyld(auVar12,auVar14);
                auVar33 = _qmtc2(auVar14._0_4_);
                pauVar4 = (undefined1 (*) [16])*piRam0028eeb8;
                auVar14 = _sqc2(auVar18);
                *pauVar4 = auVar14;
                *piVar5 = (int)(pauVar4 + 1);
                piVar5 = piRam0028eeb8;
                auVar14 = _lqc2(auStack_120);
                puVar3 = (undefined4 *)*piRam0028eeb8;
                auVar34 = _lqc2(auStack_150);
                auVar19 = _lqc2(auStack_140);
                auVar18 = _lqc2(auStack_130);
                _vmulabc(auVar34,auVar33);
                _vmaddabc(auVar19,auVar33);
                _vmaddabc(auVar18,auVar33);
                auVar14 = _vmaddbc(auVar14,auVar33);
                *puVar3 = auVar16._0_4_;
                puVar3[1] = auVar16._4_4_;
                puVar3[2] = auVar16._8_4_;
                puVar3[3] = auVar16._12_4_;
                auVar14 = _vftoi0(auVar14);
                *piVar5 = (int)(puVar3 + 4);
                piVar5 = piRam0028eeb8;
                puVar3 = (undefined4 *)*piRam0028eeb8;
                *puVar3 = uVar22;
                puVar3[1] = uVar24;
                puVar3[2] = uVar25;
                puVar3[3] = uVar26;
                *piVar5 = (int)(puVar3 + 4);
                piVar5 = piRam0028eeb8;
                pauVar4 = (undefined1 (*) [16])*piRam0028eeb8;
                auVar14 = _sqc2(auVar14);
                *pauVar4 = auVar14;
                *piVar5 = (int)(pauVar4 + 1);
              }
              auVar14 = _pextlw(lVar21,lVar20);
              auVar14 = _pcpyld(auVar36,auVar14);
              auVar18 = _lqc2(auStack_120);
              puVar3 = (undefined4 *)*piRam0028eeb8;
              auVar16 = _pextlw(lVar8,lVar23);
              auVar34 = _lqc2(auStack_150);
              auVar16 = _pcpyld(auVar12,auVar16);
              auVar19 = _lqc2(auStack_140);
              *piRam0028eeb8 = (int)(puVar3 + 4);
              auVar33 = _qmtc2(auVar16._0_4_);
              auVar16 = _lqc2(auStack_130);
              _vmulabc(auVar34,auVar33);
              _vmaddabc(auVar19,auVar33);
              _vmaddabc(auVar16,auVar33);
              auVar16 = _vmaddbc(auVar18,auVar33);
              *puVar3 = auVar14._0_4_;
              puVar3[1] = auVar14._4_4_;
              puVar3[2] = auVar14._8_4_;
              puVar3[3] = auVar14._12_4_;
              piVar5 = piRam0028eeb8;
              auVar14 = _vftoi0(auVar16);
              iStack_ec = iStack_ec + 1;
              iStack_f0 = iStack_f0 + 1;
              puVar3 = (undefined4 *)*piRam0028eeb8;
              *puVar3 = uVar22;
              puVar3[1] = uVar24;
              puVar3[2] = uVar25;
              puVar3[3] = uVar26;
              *piVar5 = (int)(puVar3 + 4);
              piVar5 = piRam0028eeb8;
              pauVar4 = (undefined1 (*) [16])*piRam0028eeb8;
              auVar14 = _sqc2(auVar14);
              *pauVar4 = auVar14;
              *piVar5 = (int)(pauVar4 + 1);
              FUN_00110688();
              FUN_00110148();
              iVar17 = *(int *)(param_11 + 4);
              fStack_110 = fStack_110 + fVar32;
            } while (iStack_ec < iVar17);
            iVar13 = *(int *)(param_11 + 8);
          }
          fStack_10c = fStack_10c + fVar31;
          iStack_e8 = iStack_e8 + 1;
        } while (iStack_e8 < iVar13);
      }
      FUN_00110688();
    }
    else {
      FUN_001116b0(param_1,param_2,param_3,param_4,param_9,iStack_f4);
    }
  }
  return;
}

