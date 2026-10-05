
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00229080(float param_1,int param_2)

{
  char cVar1;
  short sVar2;
  undefined4 uVar3;
  bool bVar4;
  undefined1 in_zero_qw [16];
  int iVar5;
  int iVar6;
  int iVar7;
  undefined8 uVar8;
  long lVar9;
  ulong uVar10;
  long lVar11;
  undefined1 auVar12 [16];
  undefined1 auVar13 [16];
  undefined1 auVar14 [16];
  int iVar15;
  undefined4 *puVar16;
  uint uVar17;
  undefined4 *puVar18;
  float fVar19;
  undefined1 in_vf0 [16];
  undefined1 auVar20 [16];
  undefined1 auVar21 [16];
  undefined1 auStack_80 [16];
  uint uStack_70;
  undefined1 (*pauStack_6c) [16];
  
  iGpffff947c = param_2;
  uVar8 = FUN_001213d8(*(undefined4 *)(param_2 + 4));
  if (iGpffff93d8 != 0) {
    FUN_00127470();
    FUN_0021b200();
  }
  pauGpffff93f8 = (undefined1 (*) [16])(param_2 + 0x50);
  puVar18 = (undefined4 *)uVar8;
  uVar3 = *puVar18;
  pauStack_6c = pauGpffff93f8;
  if ((int)puVar18[5] < 0) {
    auVar12 = _pextuw(in_zero_qw,*pauGpffff93f8);
    iVar5 = FUN_00121cd0(auVar12._0_4_,uVar8);
    uVar3 = *(undefined4 *)(iVar5 * 4 + puVar18[0x15]);
  }
  lVar9 = FUN_0021b710(uVar3);
  iGpffff9474 = 0;
  fVar19 = 1.0;
  fGpffff9478 = 1.0;
  if (((*(long *)(param_2 + 0x60) << 10) >> 0x20 & 1U) != 0) {
    if (iGpffff937c != 0) {
      fVar19 = ABS(*(float *)(iGpffff937c + 0x20));
    }
    fVar19 = (fVar19 * param_1) / (float)puVar18[0x12];
    if (fVar19 < 0.5) {
      lVar11 = *(long *)(param_2 + 0x60);
      goto LAB_002291c8;
    }
    fGpffff9478 = 1.0;
    iGpffff9474 = 1;
    if (0.0 <= fVar19) {
      fGpffff9478 = 1.0 - (float)((int)fVar19 * (uint)(fVar19 < 1.0) |
                                 (uint)(fVar19 >= 1.0) * 0x3f800000);
    }
    fGpffff9478 = fGpffff9478 + fGpffff9478;
  }
  lVar11 = *(long *)(param_2 + 0x60);
LAB_002291c8:
  iGpffff93f4 = 0;
  if ((((lVar11 << 0x1c) >> 0x20 & 1U) == 0) ||
     (uVar10 = (lVar11 << 0x1a) >> 0x20 & 0xff, uVar10 == 0xff)) {
    DAT_70003560 = 1.0;
    uStack_70 = 1;
  }
  else {
    uStack_70 = 0;
    DAT_70003560 = (float)(int)uVar10 * fGpffff80f4;
  }
  if (uStack_70 < 2) {
    do {
      uGpffff9468 = (uint)(uStack_70 == 0);
      pauGpffff93f8 = pauStack_6c;
      if (lVar9 == 0) {
LAB_00229450:
        iVar5 = puVar18[5];
      }
      else {
        bVar4 = true;
        fGpffff9408 = DAT_70003560;
        iVar5 = (int)lVar9;
        if ((iGpffff93e0 == 0) && (lVar11 = FUN_0022a110(lVar9,pauStack_6c), lVar11 != 0)) {
          lVar11 = FUN_00229d50(iVar5 + 4,param_2 + 0x10,pauGpffff93f8);
          bVar4 = lVar11 == 0;
        }
        else {
          DAT_700035a0 = 0;
        }
        puVar16 = (undefined4 *)(param_2 + 0x10);
        if (!bVar4) goto LAB_00229450;
        auVar14 = _pextlw((long)*(int *)(iVar5 + 0xc),(long)*(int *)(iVar5 + 4));
        auVar12 = _pextlw(0,(long)*(int *)(iVar5 + 0x14));
        auVar13 = _pextlw((long)*(int *)(iVar5 + 0x10),(long)*(int *)(iVar5 + 8));
        auVar14 = _pcpyld(auVar12,auVar14);
        auVar12 = _pextlw(0,(long)*(int *)(iVar5 + 0x18));
        auVar12 = _pcpyld(auVar12,auVar13);
        auVar13 = _qmtc2(auVar14._0_4_);
        auVar14 = _qmtc2(auVar12._0_4_);
        auVar12 = _vabs(auVar13);
        auVar13 = _vabs(auVar14);
        auVar12 = _vmax(auVar12,auVar13);
        _DAT_700034e0 = _sqc2(auVar12);
        DAT_70003060 = *puVar16;
        DAT_70003064 = *(undefined4 *)(param_2 + 0x14);
        DAT_70003068 = *(undefined4 *)(param_2 + 0x18);
        DAT_7000306c = *(undefined4 *)(param_2 + 0x1c);
        DAT_70003070 = *(undefined4 *)(param_2 + 0x20);
        DAT_70003074 = *(undefined4 *)(param_2 + 0x24);
        DAT_70003078 = *(undefined4 *)(param_2 + 0x28);
        DAT_7000307c = *(undefined4 *)(param_2 + 0x2c);
        auVar12 = *(undefined1 (*) [16])(param_2 + 0x30);
        DAT_70003080 = auVar12._0_4_;
        DAT_70003084 = auVar12._4_4_;
        DAT_70003088 = auVar12._8_4_;
        DAT_7000308c = auVar12._12_4_;
        _lqc2(*pauGpffff93f8);
        auVar13 = _vmove(in_vf0);
        _sqc2(auVar13);
        auVar20 = _lqc2(*pauGpffff9380);
        auVar14 = _lqc2(pauGpffff9380[1]);
        auVar12 = _lqc2(pauGpffff9380[2]);
        _vmulabc(auVar20,auVar13);
        _vmaddabc(auVar14,auVar13);
        auVar12 = _vmaddbc(auVar12,auVar13);
        _DAT_70003090 = _sqc2(auVar12);
        uGpffff9430 = uVar3;
        puGpffff9434 = puVar16;
        if (*(short *)(iVar5 + 0x1c) == 0) {
LAB_0022940c:
          sVar2 = *(short *)(iVar5 + 0x28);
        }
        else {
          if (iGpffff9474 == 0) {
            iVar6 = *(int *)(param_2 + 0x68);
            if (((*(long *)(param_2 + 0x60) << 0x1d) >> 0x20 & 1U) != 0) {
              auVar21 = _lqc2(*pauGpffff93f8);
              auVar20 = _lqc2(pauGpffff9380[3]);
              auVar13 = _lqc2(*pauGpffff9380);
              auVar14 = _lqc2(pauGpffff9380[1]);
              auVar12 = _lqc2(pauGpffff9380[2]);
              _vmulabc(auVar13,auVar21);
              _vmaddabc(auVar14,auVar21);
              _vmaddabc(auVar12,auVar21);
              auVar12 = _vmaddbc(auVar20,auVar21);
              auStack_80 = _sqc2(auVar12);
              if (iVar6 != 0) {
                do {
                  FUN_0021b6e0(*(undefined4 *)(iVar6 + 0xc0));
                  FUN_001283d0(iVar6,puVar16,auStack_80);
                  iVar6 = *(int *)(iVar6 + 0xd4);
                } while (iVar6 != 0);
                iVar6 = *(int *)(param_2 + 0x68);
              }
            }
            FUN_00229fa8(uVar3,lVar9,DAT_700035a0,iVar6);
            goto LAB_0022940c;
          }
          sVar2 = *(short *)(iVar5 + 0x28);
        }
        if ((sVar2 == 0) && (iGpffff9474 == 0)) {
          iVar5 = puVar18[5];
        }
        else {
          if ((DAT_700035a0 & 0xa2a) == 0) {
            FUN_0022a048(uVar3,0);
            goto LAB_00229450;
          }
          FUN_0022a048(uVar3,1);
          iVar5 = puVar18[5];
        }
      }
      if ((-1 < iVar5) && (*(char *)((int)puVar18 + 0x11) != '\0')) {
        iVar5 = param_2 + 0x10;
        uGpffff946c = 0;
        FUN_0021b7a8(iVar5,pauGpffff9380,pauGpffff93f8);
        if (*(char *)((int)puVar18 + 0x12) == '\0') {
          iVar6 = *(int *)(param_2 + 0x6c);
          iVar7 = puVar18[0x15];
          if (iVar6 == 0) {
            uVar17 = (uint)*(byte *)((int)puVar18 + 0x11);
            if (uVar17 != 0) {
              do {
                uVar17 = uVar17 - 1;
                FUN_002296c8(0,iVar7,iVar5);
                iVar7 = iVar7 + 0x2c;
              } while (0 < (int)uVar17);
            }
          }
          else {
            uVar17 = (uint)*(byte *)((int)puVar18 + 0x11);
            if (uVar17 != 0) {
              do {
                if ((*(uint *)(iVar7 + 4) & 0x10000) == 0) {
                  iVar15 = iVar6 + 0x10;
                  FUN_002296c8(iVar6,iVar7,iVar5);
                }
                else {
                  if ((*(uint *)(iVar6 + 8) & 1) != 0) {
                    FUN_002296c8(iVar6,iVar7,iVar5);
                  }
                  iVar15 = iVar6 + 0x40;
                }
                uVar17 = uVar17 - 1;
                iVar7 = iVar7 + 0x2c;
                iVar6 = iVar15;
              } while (0 < (int)uVar17);
            }
          }
        }
        else {
          iVar7 = 0;
          auVar12 = _pextuw(in_zero_qw,*pauGpffff93f8);
          iVar6 = FUN_00121cd0(auVar12._0_4_,uVar8);
          if (*(int *)(param_2 + 0x6c) != 0) {
            iVar7 = *(int *)(param_2 + 0x6c) + iVar6 * 0x10;
          }
          FUN_002296c8(iVar7,puVar18[0x15] + iVar6 * 0x2c,iVar5);
        }
      }
      if (iGpffff93d8 != 0) {
        FUN_00127fa8();
        FUN_00128508();
      }
      uStack_70 = uStack_70 + 1;
    } while ((int)uStack_70 < 2);
    cVar1 = *(char *)((int)puVar18 + 0xe);
  }
  else {
    cVar1 = *(char *)((int)puVar18 + 0xe);
  }
  if (cVar1 != '\0') {
    FUN_00127fa8();
    FUN_00128508();
  }
  if ((iGpffff93f4 != 0) && (lVar9 = FUN_0021d358(), lVar9 != 0)) {
    iVar6 = (int)lVar9;
    *(undefined4 *)(iVar6 + 0x10) = 0;
    *(undefined4 *)(iVar6 + 0xc) = 4;
    iVar5 = *(int *)(param_2 + 0x74);
    *(float *)(iVar6 + 0x14) = param_1;
    if (iVar5 != 0) {
      iVar7 = 0;
      if (*(char *)((int)puVar18 + 0x12) != '\0') {
        auVar12 = _pextuw(in_zero_qw,*(undefined1 (*) [16])(param_2 + 0x50));
        iVar7 = FUN_00121cd0(auVar12._0_4_,uVar8);
        iVar5 = *(int *)(param_2 + 0x74);
      }
      *(int *)(iVar6 + 0x10) = iVar5 + iVar7 * 0x10;
    }
    lVar11 = *(long *)(param_2 + 0x60);
    *(undefined4 *)(iGpffff93f4 + 0x5c) = 0;
    *(uint *)(iVar6 + 0x18) = (uint)((ulong)(lVar11 << 0x1f) >> 0x20) & 1;
    if (((*(long *)(param_2 + 0x60) << 0x1e) >> 0x20 & 1U) != 0) {
      *(undefined4 *)(iGpffff93f4 + 0x5c) = *(undefined4 *)(param_2 + 0x68);
    }
    *(int *)(iVar6 + 0x24) = param_2;
    *(int *)(iVar6 + 0x20) = iGpffff93f4;
    FUN_00126fb0(lVar9);
  }
  return;
}

