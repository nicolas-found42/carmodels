
void FUN_001939f0(int param_1)

{
  int *piVar1;
  int iVar2;
  int iVar3;
  bool bVar4;
  int *piVar5;
  int iVar6;
  undefined4 uVar9;
  undefined8 uVar7;
  long lVar8;
  undefined4 uVar10;
  undefined4 uVar11;
  int iVar12;
  ulong uVar13;
  float fVar14;
  float fVar15;
  float fVar16;
  float fVar17;
  undefined1 in_vf0 [16];
  undefined1 auVar18 [16];
  undefined1 auVar19 [16];
  undefined4 uStack_160;
  undefined4 uStack_15c;
  undefined4 uStack_158;
  undefined4 uStack_154;
  undefined4 uStack_150;
  undefined4 uStack_14c;
  undefined4 uStack_148;
  undefined4 uStack_144;
  undefined4 uStack_140;
  undefined4 uStack_13c;
  undefined4 uStack_138;
  undefined4 uStack_134;
  undefined1 auStack_130 [16];
  undefined1 auStack_120 [64];
  undefined1 auStack_e0 [64];
  undefined1 auStack_a0 [64];
  
  fVar17 = 0.0;
  iVar12 = *(int *)(param_1 + 4);
  piVar1 = *(int **)(iVar12 + 0x10c);
  iVar2 = *(int *)(iVar12 + 0x104);
  if ((*(ulong *)(iVar12 + 0xa0) & 0x20) == 0) {
    fVar17 = *(float *)(iVar12 + 0xa4) - FLOAT_0029016c;
  }
  FUN_0018c818();
  iVar6 = *(int *)(iVar12 + 0x84);
  if (iVar6 == 0) {
LAB_00193ae0:
    iVar6 = *(int *)(param_1 + 4);
  }
  else {
    uStack_160 = *(undefined4 *)(iVar6 + 0x30);
    uStack_15c = *(undefined4 *)(iVar6 + 0x34);
    uStack_158 = *(undefined4 *)(iVar6 + 0x38);
    uStack_154 = *(undefined4 *)(iVar6 + 0x3c);
    auVar18 = _lqc2(*(undefined1 (*) [16])(iVar6 + 0x600));
    uStack_150 = *(undefined4 *)(iVar6 + 0x40);
    uStack_14c = *(undefined4 *)(iVar6 + 0x44);
    uStack_148 = *(undefined4 *)(iVar6 + 0x48);
    uStack_144 = *(undefined4 *)(iVar6 + 0x4c);
    auVar19 = _qmtc2(0x3f800000);
    uStack_140 = *(undefined4 *)(iVar6 + 0x50);
    uStack_13c = *(undefined4 *)(iVar6 + 0x54);
    uStack_138 = *(undefined4 *)(iVar6 + 0x58);
    uStack_134 = *(undefined4 *)(iVar6 + 0x5c);
    _sqc2(auVar18);
    auVar18 = _vmulbc(in_vf0,auVar19);
    auStack_130 = _sqc2(auVar18);
    FUN_00114098(*(int *)(param_1 + 4) + 0x20,&uStack_160);
    iVar6 = *(int *)(iVar12 + 0x84);
    iVar3 = *(int *)(param_1 + 4);
    uVar9 = *(undefined4 *)(iVar6 + 0x604);
    uVar10 = *(undefined4 *)(iVar6 + 0x608);
    uVar11 = *(undefined4 *)(iVar6 + 0x60c);
    *(undefined4 *)(iVar3 + 0x50) = *(undefined4 *)(iVar6 + 0x600);
    *(undefined4 *)(iVar3 + 0x54) = uVar9;
    *(undefined4 *)(iVar3 + 0x58) = uVar10;
    *(undefined4 *)(iVar3 + 0x5c) = uVar11;
    uVar9 = *(undefined4 *)(iVar6 + 0x654);
    uVar10 = *(undefined4 *)(iVar6 + 0x658);
    uVar11 = *(undefined4 *)(iVar6 + 0x65c);
    *(undefined4 *)(iVar3 + 0x60) = *(undefined4 *)(iVar6 + 0x650);
    *(undefined4 *)(iVar3 + 100) = uVar9;
    *(undefined4 *)(iVar3 + 0x68) = uVar10;
    *(undefined4 *)(iVar3 + 0x6c) = uVar11;
    if (piVar1 == (int *)0x0) {
      FUN_001320a0(iVar2);
      goto LAB_00193ae0;
    }
    FUN_001318e8(piVar1);
    iVar6 = *(int *)(param_1 + 4);
  }
  if ((*(ulong *)(iVar6 + 0xa0) & 0x20) != 0) {
    iVar12 = *(int *)(iVar6 + 0x10);
    goto LAB_00193c94;
  }
  if (fVar17 <= 0.0) {
    if (((*(ulong *)(iVar6 + 0xa0) & 4) == 0) && (*(int *)(iVar12 + 0x84) == 0)) {
      *(undefined4 *)(iVar6 + 0xa4) = 0x41200000;
    }
    else {
      uVar7 = FUN_001ae3b8();
      piVar5 = (int *)FUN_001ae3b8();
      bVar4 = true;
      lVar8 = (**(code **)(&DAT_0023c2e0 + *piVar5 * 0x5c))(uVar7,0x10);
      if (lVar8 != 0) {
        fVar17 = 10000.0;
        iVar6 = *(int *)((int)lVar8 + 4);
        while( true ) {
          fVar16 = *(float *)(iVar6 + 0x74);
          fVar15 = *(float *)(*(int *)(param_1 + 4) + 0xa8);
          fVar14 = (float)FUN_00115300(*(undefined8 *)(*(int *)(param_1 + 4) + 0x50),
                                       *(undefined8 *)(iVar6 + 0x50));
          fVar15 = (fVar16 - fVar15) * *(float *)(iRam00290534 + 0x54);
          fVar15 = fVar15 * fVar15;
          if ((float)((int)fVar15 * (uint)(fVar15 < fVar14) | (int)fVar14 * (uint)(fVar15 >= fVar14)
                     ) < fVar17) {
            bVar4 = false;
          }
          lVar8 = (**(code **)(&DAT_0023dcc0 + *(int *)lVar8 * 0x5c))(lVar8,0x10);
          if (lVar8 == 0) break;
          iVar6 = *(int *)((int)lVar8 + 4);
        }
      }
      if (bVar4) {
        if (piVar1 == (int *)0x0) {
          iVar6 = *(int *)(param_1 + 4);
        }
        else {
          *(ulong *)(*(int *)(param_1 + 4) + 0xa0) =
               *(ulong *)(*(int *)(param_1 + 4) + 0xa0) & 0xfffffffffffffffb;
          FUN_0012f5c0(piVar1);
          FUN_00114098(*(int *)(param_1 + 4) + 0x20,*piVar1 + 0x10);
          iVar6 = *(int *)(param_1 + 4);
          if (*(int *)(iVar6 + 0x84) == 0) {
            *(undefined4 *)(iVar6 + 0xa4) = 0x41200000;
            goto LAB_00193c60;
          }
          FUN_00194648(*(undefined4 *)(iVar12 + 0x84));
          iVar6 = *(int *)(param_1 + 4);
          *(undefined4 *)(iVar6 + 0x84) = 0;
        }
      }
      else {
        iVar6 = *(int *)(param_1 + 4);
      }
      *(undefined4 *)(iVar6 + 0xa4) = 0x41200000;
    }
  }
  else {
    *(float *)(iVar6 + 0xa4) = fVar17;
  }
LAB_00193c60:
  uVar13 = *(ulong *)(iVar2 + 0x60);
  *(ulong *)(iVar6 + 0xa0) = *(ulong *)(iVar6 + 0xa0) | 8;
  *(ulong *)(iVar2 + 0x60) = uVar13 & 0xfffffffffffffffe | 1;
  iVar12 = *(int *)(iVar6 + 0x10);
LAB_00193c94:
  if (iVar12 == 1) {
    FUN_00114098(auStack_120,iVar6 + 0x20);
    FUN_00113aa8((FLOAT_0029016c - (float)(int)FLOAT_0029016c) * 6.283185,0,0,0,0,0,auStack_a0);
    FUN_00115560(auStack_e0,auStack_a0,auStack_120);
    FUN_00114098(*(int *)(param_1 + 4) + 0x20,auStack_e0);
  }
  return;
}

