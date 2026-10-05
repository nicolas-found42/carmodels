
/* WARNING: Removing unreachable block (ram,0x0019b544) */
/* WARNING: Removing unreachable block (ram,0x0019b600) */

void FUN_0019b3e8(int param_1)

{
  short sVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  undefined *puVar5;
  undefined8 *puVar6;
  undefined8 *puVar7;
  float fVar8;
  
  iVar3 = *(int *)(param_1 + 4);
  sVar1 = *(short *)(iVar3 + 0x14);
  if (sVar1 < 0) {
    puVar5 = (undefined *)0x0;
    iVar2 = iRam000000e8;
  }
  else {
    iVar2 = (sVar1 * 0x14 + (int)sVar1) * 0x10;
    puVar5 = &DAT_00241b40 + iVar2;
    iVar2 = *(int *)(&DAT_00241c28 + iVar2);
  }
  puVar6 = (undefined8 *)(iVar3 + 0x50);
  puVar7 = (undefined8 *)(iVar3 + 0x60);
  if (iVar2 == 0) {
    if (0.0 < *(float *)(puVar5 + 0x10c)) {
      *(float *)(puVar5 + 0x10c) = *(float *)(puVar5 + 0x10c) - FLOAT_0029016c;
      goto LAB_0019b4a0;
    }
    iVar3 = *(int *)(puVar5 + 0xec);
  }
  else {
    if (*(float *)(puVar5 + 0x10c) <= 0.0) {
      FUN_0019c208(*(undefined4 *)(iVar3 + 0xec),0x3f800000,puVar6,puVar7);
    }
    *(float *)(puVar5 + 0x10c) = 0.39999998;
LAB_0019b4a0:
    iVar3 = *(int *)(puVar5 + 0xec);
  }
  if (iVar3 == 0) {
    if (0.0 < *(float *)(puVar5 + 0x110)) {
      *(float *)(puVar5 + 0x110) = *(float *)(puVar5 + 0x110) - FLOAT_0029016c;
      goto LAB_0019b504;
    }
    iVar3 = *(int *)(puVar5 + 0xf0);
  }
  else {
    if (*(float *)(puVar5 + 0x110) <= 0.0) {
      FUN_0019c208(*(undefined4 *)(*(int *)(param_1 + 4) + 0xec),0x3f800000,puVar6,puVar7);
    }
    *(float *)(puVar5 + 0x110) = 0.39999998;
LAB_0019b504:
    iVar3 = *(int *)(puVar5 + 0xf0);
  }
  if (iVar3 == 0) {
    if (0.0 < *(float *)(puVar5 + 0x114)) {
      *(float *)(puVar5 + 0x114) = *(float *)(puVar5 + 0x114) - FLOAT_0029016c;
      goto LAB_0019b5d8;
    }
    iVar3 = *(int *)(puVar5 + 0xf4);
  }
  else {
    if (*(int *)(*(int *)(*(int *)(param_1 + 4) + 0x14c) + 0x140) == 3) {
      iVar3 = 0x14;
      iRam00290058 = iRam00290058 * 0x41c64e6d + 0x3039;
      uVar4 = (iRam00290058 >> 0x10 & 0x7fffU) % 3;
      fVar8 = *(float *)(puVar5 + 0x114);
    }
    else {
      iVar3 = 1;
      iRam00290058 = iRam00290058 * 0x41c64e6d + 0x3039;
      uVar4 = iRam00290058 >> 0x10 & 3;
      fVar8 = *(float *)(puVar5 + 0x114);
    }
    if (fVar8 <= 0.0) {
      FUN_00195898(0x3f800000,iVar3 + uVar4,*puVar6,*puVar7);
    }
    *(float *)(puVar5 + 0x114) = 0.39999998;
LAB_0019b5d8:
    iVar3 = *(int *)(puVar5 + 0xf4);
  }
  if (iVar3 == 0) {
    if (*(float *)(puVar5 + 0x118) <= 0.0) {
      *(undefined4 *)(puVar5 + 0xf4) = 0;
      goto LAB_0019b674;
    }
    *(float *)(puVar5 + 0x118) = *(float *)(puVar5 + 0x118) - FLOAT_0029016c;
  }
  else {
    iRam00290058 = iRam00290058 * 0x41c64e6d + 0x3039;
    if (0.0 < *(float *)(puVar5 + 0x118)) {
      *(undefined4 *)(puVar5 + 0xf4) = 0;
      goto LAB_0019b674;
    }
    FUN_00195898(0x3f800000,(iRam00290058 >> 0x10 & 0x7fffU) % 3 + 0xc,*puVar6,*puVar7);
    *(undefined4 *)(puVar5 + 0x118) = 0x3e800000;
  }
  *(undefined4 *)(puVar5 + 0xf4) = 0;
LAB_0019b674:
  *(undefined4 *)(puVar5 + 0xec) = 0;
  *(undefined4 *)(puVar5 + 0xe8) = 0;
  *(undefined4 *)(puVar5 + 0xf0) = 0;
  return;
}

