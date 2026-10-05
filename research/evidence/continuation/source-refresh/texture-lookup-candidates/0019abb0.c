
void FUN_0019abb0(int param_1)

{
  int iVar1;
  undefined4 uVar2;
  float fVar3;
  int iVar4;
  undefined4 *puVar5;
  int iVar6;
  int *piVar7;
  float fVar8;
  float fVar9;
  float fVar10;
  undefined1 in_vf0 [16];
  undefined1 auVar11 [16];
  undefined1 auVar12 [16];
  undefined1 auVar13 [16];
  undefined1 auStack_140 [64];
  undefined1 auStack_100 [64];
  undefined1 auStack_c0 [32];
  undefined1 auStack_a0 [16];
  undefined1 auStack_90 [16];
  undefined1 auStack_80 [16];
  
  iVar1 = *(int *)(param_1 + 4);
  if (ABS(*(float *)(iVar1 + 0xec)) < 10.0) {
    if ((*(uint *)(*(int *)(iVar1 + 0xe4) + 0x60) & 1) == 0) {
      iVar4 = *(int *)(iVar1 + 0x210);
    }
    else if ((float)((uint)((ulong)(*(long *)(*(int *)(iVar1 + 0xe4) + 0x60) << 0x1a) >> 0x20) &
                    0xff) <= 128.0) {
      iVar4 = *(int *)(iVar1 + 0x210);
    }
    else {
      iVar4 = *(int *)(iVar1 + 0x210);
      if (*(int *)(iVar1 + 0x94) != 0) {
        iVar6 = 0;
        if (iVar4 < 1) {
          return;
        }
        fVar10 = 1.0;
        fVar8 = 4.0;
        puVar5 = (undefined4 *)(iVar1 + 0x238);
        piVar7 = (int *)(iVar1 + 0x224);
        do {
          FUN_00137898(0,*puVar5);
          FUN_00114098(auStack_140,*(int *)(param_1 + 4) + 0x20);
          iVar4 = *piVar7;
          piVar7 = piVar7 + 1;
          FUN_00113aa8(*(undefined4 *)(iVar4 + 0x10),*(undefined4 *)(iVar4 + 0x14),
                       *(undefined4 *)(iVar4 + 0x18),*(undefined4 *)(iVar4 + 4),
                       *(undefined4 *)(iVar4 + 8),*(undefined4 *)(iVar4 + 0xc),auStack_100);
          FUN_00115560(auStack_c0,auStack_100,auStack_140);
          FUN_00137910(*puVar5,auStack_90);
          fVar9 = *(float *)(*(int *)(param_1 + 4) + 0xf4) /
                  *(float *)(*(int *)(*(int *)(*(int *)(param_1 + 4) + 0x14c) + 0x188) + 0x2c);
          FUN_0020c7fc(auStack_80,0,0x10);
          auVar13 = _qmtc2(fVar10 - fVar9);
          if (0.5 < *(float *)(*(int *)(*(int *)(param_1 + 4) + 0xe0) + 0x78)) {
            auVar12 = _lqc2(auStack_a0);
            fVar3 = fVar8;
          }
          else {
            auVar12 = _lqc2(auStack_a0);
            fVar3 = fVar9 * fVar8;
          }
          auVar11 = _qmtc2(fVar3);
          auVar12 = _vmulbc(auVar12,auVar11);
          auVar12 = _sqc2(auVar12);
          auVar11 = _lqc2(auVar12);
          iVar6 = iVar6 + 1;
          auVar12 = _lqc2(*(undefined1 (*) [16])(*(int *)(param_1 + 4) + 0x60));
          auVar12 = _vadd(auVar11,auVar12);
          _sqc2(auVar12);
          auVar13 = _vaddbc(in_vf0,auVar13);
          auStack_80 = _sqc2(auVar13);
          FUN_00137930(0.39999998,(fVar10 - fVar9) * 0.5,fVar9 * 5.0 + 9.0,*puVar5,1);
          uVar2 = *puVar5;
          puVar5 = puVar5 + 1;
          FUN_00137920(uVar2,auStack_80);
        } while (iVar6 < *(int *)(iVar1 + 0x210));
        return;
      }
    }
  }
  else {
    iVar4 = *(int *)(iVar1 + 0x210);
  }
  iVar6 = 0;
  if (0 < iVar4) {
    puVar5 = (undefined4 *)(iVar1 + 0x238);
    uVar2 = *puVar5;
    while( true ) {
      puVar5 = puVar5 + 1;
      iVar6 = iVar6 + 1;
      FUN_001378a8(uVar2);
      if (*(int *)(iVar1 + 0x210) <= iVar6) break;
      uVar2 = *puVar5;
    }
  }
  return;
}

