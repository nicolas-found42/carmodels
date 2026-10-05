
/* source file (string position, lower evidence than a direct reference):
   ../fr2/source/entity/mobile/vehicle/car/car.c */

void FUN_0019b900(undefined8 param_1,int param_2,undefined4 param_3,undefined1 *param_4)

{
  int iVar1;
  undefined4 uVar2;
  long lVar3;
  long lVar4;
  int iVar5;
  int iVar6;
  int iVar7;
  undefined4 uStack_a0;
  undefined4 uStack_9c;
  int iStack_98;
  undefined4 uStack_94;
  undefined1 auStack_80 [4];
  undefined4 uStack_7c;
  undefined4 uStack_78;
  undefined4 uStack_74;
  int iStack_60;
  
  iVar7 = 0;
  iStack_60 = param_2;
  lVar3 = FUN_00124e98(param_1,(&PTR_s_WHEEL_FRONT_LEFT_0023acf0)[param_2]);
  if (lVar3 != -1) {
    iStack_98 = 0;
    while (iVar7 = iStack_98, uStack_a0 = param_3, uStack_94 = (int)lVar3,
          lVar4 = FUN_001231c0(&uStack_a0), lVar4 == 1) {
      iStack_98 = iVar7 + 1;
    }
  }
  iVar5 = iVar7 << 2;
  if (0 < iVar7) {
    param_4[1] = (char)iVar7;
    uVar2 = FUN_0010d020(iVar5);
    *(undefined4 *)(param_4 + 8) = uVar2;
    uVar2 = FUN_0010d020(iVar5);
    *(undefined4 *)(param_4 + 0x10) = uVar2;
    uVar2 = FUN_0010d020(iVar5);
    *(undefined4 *)(param_4 + 0x14) = uVar2;
    FUN_0020c7fc(*(undefined4 *)(param_4 + 8),0,iVar5);
    FUN_0020c7fc(*(undefined4 *)(param_4 + 0x10),0,iVar5);
    FUN_0020c7fc(*(undefined4 *)(param_4 + 0x14),0,iVar5);
    iStack_98 = 0;
    while (iVar7 = iStack_98, uStack_a0 = param_3, uStack_94 = (int)lVar3,
          lVar4 = FUN_001231c0(&uStack_a0), lVar4 == 1) {
      iVar6 = iVar7 * 4;
      iVar5 = *(int *)(param_4 + 0x14);
      iVar7 = iVar7 + 1;
      iVar1 = *(int *)(param_4 + 0x10);
      uStack_78 = 0;
      *(undefined4 *)(iVar6 + *(int *)(param_4 + 8)) = uStack_9c;
      *(undefined4 *)(iVar6 + iVar5) = 0;
      *(undefined4 *)(iVar6 + iVar1) = 0;
      uStack_74 = FUN_00124e98(param_1,0x261600);
      lVar4 = FUN_001232a8(&uStack_a0,auStack_80);
      if (lVar4 == 1) {
        *(undefined4 *)(iVar6 + *(int *)(param_4 + 0x14)) = uStack_7c;
      }
      uStack_78 = 0;
      uStack_74 = FUN_00124e98(param_1,0x261610);
      lVar4 = FUN_001232a8(&uStack_a0,auStack_80);
      iStack_98 = iVar7;
      if (lVar4 == 1) {
        *(undefined4 *)(iVar6 + *(int *)(param_4 + 0x10)) = uStack_7c;
      }
    }
  }
  iVar7 = 0;
  lVar3 = FUN_00124e98(param_1,(&PTR_s_HUB_FRONT_LEFT_002432e0)[param_2]);
  if (lVar3 != -1) {
    iStack_98 = 0;
    while (iVar7 = iStack_98, uStack_a0 = param_3, uStack_94 = (int)lVar3,
          lVar4 = FUN_001231c0(&uStack_a0), lVar4 == 1) {
      iStack_98 = iVar7 + 1;
    }
  }
  if (0 < iVar7) {
    *param_4 = (char)iVar7;
    uVar2 = FUN_0010d020(iVar7 << 2);
    *(undefined4 *)(param_4 + 4) = uVar2;
    iStack_98 = 0;
    while( true ) {
      iVar7 = iStack_98;
      uStack_a0 = param_3;
      uStack_94 = (int)lVar3;
      lVar4 = FUN_001231c0(&uStack_a0);
      if (lVar4 != 1) break;
      *(undefined4 *)(iVar7 * 4 + *(int *)(param_4 + 4)) = uStack_9c;
      iStack_98 = iVar7 + 1;
    }
  }
  iVar7 = 0;
  lVar3 = FUN_00124e98(param_1,(&PTR_s_SUSPENSION_FRONT_LEFT_002432f0)[param_2]);
  if (lVar3 != -1) {
    iStack_98 = 0;
    while (iVar7 = iStack_98, uStack_a0 = param_3, uStack_94 = (int)lVar3,
          lVar4 = FUN_001231c0(&uStack_a0), lVar4 == 1) {
      iStack_98 = iVar7 + 1;
    }
  }
  if (0 < iVar7) {
    param_4[2] = (char)iVar7;
    uVar2 = FUN_0010d020(iVar7 << 2);
    *(undefined4 *)(param_4 + 0xc) = uVar2;
    iStack_98 = 0;
    while( true ) {
      iVar7 = iStack_98;
      uStack_a0 = param_3;
      uStack_94 = (int)lVar3;
      lVar4 = FUN_001231c0(&uStack_a0);
      if (lVar4 != 1) break;
      *(undefined4 *)(iVar7 * 4 + *(int *)(param_4 + 0xc)) = uStack_9c;
      iStack_98 = iVar7 + 1;
    }
  }
  if (iStack_60 < 2) {
    iVar7 = 0;
    lVar3 = FUN_00124e98(param_1,(&PTR_s_SUSPENSION_SUPPORT_LEFT_00243300)[param_2]);
    if (lVar3 != -1) {
      iStack_98 = 0;
      while (iVar7 = iStack_98, uStack_a0 = param_3, uStack_94 = (int)lVar3,
            lVar4 = FUN_001231c0(&uStack_a0), lVar4 == 1) {
        iStack_98 = iVar7 + 1;
      }
    }
    if (0 < iVar7) {
      param_4[3] = (char)iVar7;
      uVar2 = FUN_0010d020(iVar7 << 2);
      *(undefined4 *)(param_4 + 0x18) = uVar2;
      iStack_98 = 0;
      while( true ) {
        iVar7 = iStack_98;
        uStack_a0 = param_3;
        uStack_94 = (int)lVar3;
        lVar4 = FUN_001231c0(&uStack_a0);
        iStack_98 = iVar7 + 1;
        if (lVar4 != 1) break;
        *(undefined4 *)(iVar7 * 4 + *(int *)(param_4 + 0x18)) = uStack_9c;
      }
    }
  }
  return;
}

