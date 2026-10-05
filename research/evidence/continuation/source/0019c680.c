
void FUN_0019c680(int param_1,int param_2)

{
  int iVar1;
  int iVar2;
  char cVar3;
  undefined4 uVar4;
  undefined4 uVar5;
  long lVar6;
  long lVar7;
  undefined8 uVar8;
  undefined8 uVar9;
  int iVar10;
  int iVar11;
  int iVar12;
  undefined4 *puVar13;
  undefined1 auStack_70 [48];
  
  iVar1 = *(int *)(param_1 + 4);
  FUN_001154d0(iVar1 + 0x20);
  iVar2 = *(int *)(*(int *)(*(int *)(param_1 + 4) + 0x14c) + 0x174);
  lVar6 = FUN_00124cb8(*(undefined4 *)(iVar2 + 0x74),iVar2 + 0x60);
  lVar7 = FUN_0015e518();
  if (lVar7 != 0) {
    uVar8 = FUN_0015e518();
    lVar6 = FUN_00124cb8(*(undefined4 *)(iVar2 + 0x74),uVar8);
  }
  if (lVar6 != -1) {
    uVar4 = FUN_00121d98(lVar6);
    iVar12 = *(int *)(param_2 + 0x24);
    iVar10 = *(int *)(param_1 + 4);
    *(undefined4 *)(iVar1 + 0xe4) = uVar4;
    iVar10 = *(int *)(*(int *)(iVar10 + 0x14c) + 0x174);
    uVar8 = FUN_00124cb8(*(undefined4 *)(iVar10 + 0x74),iVar10 + 0x60);
    uVar9 = FUN_00125640(*(undefined4 *)(iVar10 + 0x74),(&PTR_s_INVALID_0023acb0)[iVar12]);
    cVar3 = FUN_00125700(uVar8,uVar9);
    if (cVar3 == '\0') {
      FUN_001b9508(0x261968,(&PTR_s_INVALID_0023acb0)[iVar12],
                   *(int *)(*(int *)(param_1 + 4) + 0x14c) + 2);
    }
    else {
      FUN_00121e10(*(undefined4 *)(*(int *)(param_1 + 4) + 0xe4),uVar9);
    }
    FUN_00123f18(*(undefined4 *)(iVar1 + 0xe4));
    *(int *)(*(int *)(param_1 + 4) + 0xe8) = (int)lVar6;
    uVar4 = *(undefined4 *)(iVar2 + 0x74);
    iVar1 = *(int *)(param_1 + 4);
    iVar2 = *(int *)(iVar1 + 0xe4);
    iVar12 = iVar1 + 0x150;
    iVar10 = 0;
    do {
      iVar11 = iVar10 + 1;
      FUN_0019b900(uVar4,iVar10,iVar2,iVar12);
      iVar12 = iVar12 + 0x1c;
      iVar10 = iVar11;
    } while (iVar11 < 4);
    uVar5 = FUN_0019bfe0(uVar4,iVar2,0x2619a0,iVar1 + 0x1c4,0);
    *(undefined4 *)(iVar1 + 0x1dc) = uVar5;
    uVar5 = FUN_0019bfe0(uVar4,iVar2,0x2619b0,iVar1 + 0x1c5,1);
    *(undefined4 *)(iVar1 + 0x1e0) = uVar5;
    uVar5 = FUN_0019bfe0(uVar4,iVar2,0x2619c8,iVar1 + 0x1c6,0);
    *(undefined4 *)(iVar1 + 0x1e4) = uVar5;
    uVar5 = FUN_0019bfe0(uVar4,iVar2,0x2619e0,iVar1 + 0x1c7,1);
    *(undefined4 *)(iVar1 + 0x1e8) = uVar5;
    puVar13 = (undefined4 *)(iVar1 + 0x1fc);
    iVar12 = 0;
    do {
      iVar10 = iVar12 + 1;
      FUN_00101730(auStack_70,0x20,0x2619f8,iVar10);
      uVar5 = FUN_0019bfe0(uVar4,iVar2,auStack_70,iVar1 + iVar12 + 0x1c8,0);
      puVar13[-4] = uVar5;
      FUN_00101730(auStack_70,0x20,0x261a08,iVar10);
      uVar5 = FUN_0019bfe0(uVar4,iVar2,auStack_70,iVar1 + iVar12 + 0x1cc,0);
      *puVar13 = uVar5;
      puVar13 = puVar13 + 1;
      iVar12 = iVar10;
    } while (iVar10 < 4);
    lVar7 = FUN_00125458(*(undefined4 *)(iVar2 + 4),0x28ff68);
    if (lVar7 != -1) {
      iVar12 = 0;
      lVar7 = FUN_00122260(iVar1 + 0x224,5,*(undefined4 *)(iVar2 + 4));
      *(int *)(iVar1 + 0x210) = (int)lVar7;
      if (0 < lVar7) {
        puVar13 = (undefined4 *)(iVar1 + 0x238);
        do {
          iVar12 = iVar12 + 1;
          uVar4 = FUN_00137838(8);
          iVar10 = *(int *)(iVar1 + 0x210);
          *puVar13 = uVar4;
          puVar13 = puVar13 + 1;
        } while (iVar12 < iVar10);
      }
    }
    uVar4 = FUN_0019c130(iVar2,0x261a20);
    *(undefined4 *)(iVar1 + 0x1d0) = uVar4;
    uVar4 = FUN_0019c130(iVar2,0x261a30);
    *(undefined4 *)(iVar1 + 0x1d4) = uVar4;
    uVar4 = FUN_0019c130(iVar2,0x261a40);
    *(undefined4 *)(iVar1 + 0x1d8) = uVar4;
    return;
  }
                    /* WARNING: Subroutine does not return */
  FUN_00105888(0x261918,0x1eb,0x261980,iVar2 + 0x60);
}

